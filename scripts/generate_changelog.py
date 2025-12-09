"""
生成项目 CHANGELOG 的脚本

这个脚本读取 git 提交历史,按照约定式提交格式解析并生成格式化的 changelog。
相比 git-cliff,提供更灵活的控制和自定义逻辑。

关键特性:
- 智能获取真实 GitHub 用户名(支持多层策略)
- 完美处理 squash merge 的子提交展开
- 支持 emoji 格式的约定式提交

用户名获取策略(优先级从高到低):
1. GitHub 邮箱格式提取: {id}+{username}@users.noreply.github.com -> username (自动)
2. GitHub API 查询: 使用 GITHUB_TOKEN 查询邮箱对应的用户名 (自动,推荐在 CI/CD 中使用)
3. 昵称回退: 使用原始 git 提交中的昵称 (当无法通过上述方式识别时)

用法:
    python scripts/generate_changelog.py [--output CHANGELOG.md] [--latest]

    # 本地测试示例 (自动提取 GitHub 邮箱格式)
    python scripts/generate_changelog.py --latest

    # CI/CD 示例 (使用 token 查询所有用户名)
    GITHUB_TOKEN=${{ secrets.GITHUB_TOKEN }} python scripts/generate_changelog.py -o CHANGELOG.md
"""

import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

# ============================================================================
# 常量定义
# ============================================================================

# 约定式提交正则: type[emoji](scope): message
CONVENTIONAL_COMMIT_PATTERN = re.compile(
    r"^(?P<type>\w+)(?P<emoji>[^\w\s:(]*)?(?:\((?P<scope>[^)]+)\))?\s*:\s*(?P<message>.+)$"
)

# GitHub noreply 邮箱正则: {id}+{username}@users.noreply.github.com
GITHUB_NOREPLY_EMAIL_PATTERN = re.compile(
    r"^(\d+)\+([^@]+)@users\.noreply\.github\.com$"
)

# Git log 中需要过滤的干扰文本模式
NOISE_PATTERNS = frozenset(
    [
        "Bumps [",
        "Release notes",
        "Commits]",
        "updated-dependencies:",
        "dependency-name:",
        "dependency-version:",
        "dependency-type:",
        "update-type:",
        "Signed-off-by:",
    ]
)

# Footer 关键字
FOOTER_KEYWORDS = frozenset(["Co-authored-by", "Signed-off-by"])

# 提交类型到分组的映射
TYPE_GROUPS: dict[str, tuple[str, int]] = {
    "feat": ("✨ 新功能", 0),
    "fix": ("🐛 Bug修复", 1),
    "patch": ("🐛 Bug修复", 1),
    "perf": ("🚀 性能优化", 2),
    "refactor": ("🎨 代码重构", 3),
    "format": ("🥚 格式化", 4),
    "style": ("💄 样式", 5),
    "docs": ("📚 文档", 6),
    "chore": ("🧹 日常维护", 7),
    "git": ("🧹 日常维护", 7),
    "deps": ("🧩 修改依赖", 8),
    "build": ("🧩 修改依赖", 8),
    "revert": ("🔁 还原提交", 10),
    "test": ("🧪 测试", 11),
    "file": ("📦 文件变更", 12),
    "tag": ("📌 发布", 13),
    "config": ("🔧 配置文件", 14),
    "ci": ("⚙️ 持续集成", 15),
    "init": ("🎉 初始化", 16),
    "wip": ("🚧 进行中", 17),
}

DEFAULT_GROUP = ("其他变更", 99)
COMMIT_SEPARATOR = "---COMMIT-SEPARATOR---"
GIT_LOG_FORMAT = "%H|%an|%ae|%ai|%B"


# ============================================================================
# 数据模型
# ============================================================================


@dataclass
class Commit:
    """提交信息数据类"""

    hash: str
    message: str
    author: str
    email: str
    date: datetime
    type: str = ""
    scope: str = ""
    breaking: bool = False
    footers: dict[str, str] = field(default_factory=dict)
    original_message: str = ""

    def __post_init__(self) -> None:
        """初始化后处理：保存原始消息并解析提交格式"""
        if not self.original_message:
            self.original_message = self.message
        self._parse_message()

    def _parse_message(self) -> None:
        """解析约定式提交消息"""
        lines = self.message.strip().split("\n")
        if not lines:
            return

        first_line = re.sub(r"^[-*]\s*", "", lines[0].strip())
        match = CONVENTIONAL_COMMIT_PATTERN.match(first_line)

        if match:
            self.type = match.group("type").lower()
            self.scope = match.group("scope") or ""
            self.message = match.group("message").strip()
        else:
            self._parse_non_conventional_message(first_line)

        self._parse_footers(lines[1:])

    def _parse_non_conventional_message(self, first_line: str) -> None:
        """解析非标准格式的提交消息"""
        if first_line.lower().startswith("revert"):
            self.type = "revert"
            self.message = first_line
            return

        # 尝试匹配带 emoji 的格式: type[emoji]: message
        emoji_match = re.match(r"^(\w+)([^:]*?):\s*(.+)$", first_line)
        if emoji_match:
            self.type = emoji_match.group(1).lower()
            self.message = emoji_match.group(3).strip()
        else:
            self.type = "chore"
            self.message = first_line

    def _parse_footers(self, lines: list[str]) -> None:
        """解析提交消息的 footer 部分"""
        for line in lines:
            line = line.strip()
            if ": " in line:
                key, value = line.split(": ", 1)
                if key in FOOTER_KEYWORDS:
                    self.footers[key] = value

    def get_display_message(self) -> str:
        """获取用于显示的消息（仅第一行）"""
        return self.message.split("\n")[0].strip()


# ============================================================================
# GitHub 用户名查询
# ============================================================================


class GitHubUserCache:
    """GitHub 用户名缓存与查询服务

    获取策略优先级:
    1. 从 GitHub noreply 邮箱格式提取
    2. 通过 GitHub API 查询
    3. 返回 None（由调用方决定回退策略）
    """

    GITHUB_API_HEADERS = {
        "Accept": "application/vnd.github.v3+json",
    }
    API_TIMEOUT = 5

    def __init__(self, email_to_names: dict[str, set[str]] | None = None) -> None:
        self.cache: dict[str, str | None] = {}
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.email_to_names = email_to_names or {}

    def get_github_username(self, author_name: str, author_email: str) -> str | None:
        """获取用户的真实 GitHub 用户名"""
        if not author_name:
            return None

        cache_key = f"{author_name}|{author_email}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        username = self._resolve_username(author_email)
        self.cache[cache_key] = username
        return username

    def _resolve_username(self, email: str) -> str | None:
        """按优先级解析用户名"""
        # 策略 1: 从 noreply 邮箱提取
        if email:
            username = self._extract_from_noreply_email(email)
            if username:
                return username

        # 策略 2: API 查询
        if self.github_token and email:
            return self._fetch_via_api(email)

        return None

    def _extract_from_noreply_email(self, email: str) -> str | None:
        """从 GitHub noreply 邮箱提取用户名"""
        match = GITHUB_NOREPLY_EMAIL_PATTERN.match(email)
        return match.group(2) if match else None

    def _fetch_via_api(self, email: str) -> str | None:
        """通过 GitHub API 查询用户名"""
        # 优先用邮箱搜索
        username = self._api_search_by_email(email)
        if username:
            return username

        # 回退：尝试用关联的 git 用户名验证
        email_lower = email.lower()
        for name in self.email_to_names.get(email_lower, []):
            username = self._api_verify_username(name)
            if username:
                return username

        return None

    def _github_api_request(self, url: str) -> dict[str, Any] | None:
        """统一的 GitHub API 请求方法"""
        headers = {**self.GITHUB_API_HEADERS}
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"

        try:
            req = Request(url, headers=headers)
            with urlopen(req, timeout=self.API_TIMEOUT) as response:
                return json.loads(response.read().decode())
        except (URLError, json.JSONDecodeError, TimeoutError):
            return None

    def _api_search_by_email(self, email: str) -> str | None:
        """通过邮箱搜索 GitHub 用户"""
        data = self._github_api_request(
            f"https://api.github.com/search/users?q={email}+in:email"
        )
        if data:
            items = data.get("items", [])
            if items:
                return items[0].get("login")
        return None

    def _api_verify_username(self, username: str) -> str | None:
        """验证用户名是否存在并返回规范化名称"""
        data = self._github_api_request(f"https://api.github.com/users/{username}")
        return data.get("login") if data else None


# ============================================================================
# Changelog 生成器
# ============================================================================


class ChangelogGenerator:
    """Changelog 生成器

    从 Git 仓库读取提交历史，解析约定式提交格式，生成格式化的 changelog。
    """

    def __init__(self, repo_path: Path | None = None) -> None:
        self.repo_path = repo_path or Path.cwd()
        self.email_to_names = self._build_email_to_names_map()
        self.user_cache = GitHubUserCache(self.email_to_names)

    def _run_git(self, *args) -> str:
        """运行 git 命令"""
        result = subprocess.run(
            ["git", "-C", str(self.repo_path), *args],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout

    def _build_email_to_names_map(self) -> dict[str, set[str]]:
        """构建邮箱到用户名的映射 (同一邮箱可能有多个用户名)
        
        这用于当 API 搜索邮箱找不到结果时,
        尝试用关联的其他用户名去搜 API
        """
        mapping = defaultdict(set)
        try:
            output = self._run_git("log", "--all", "--format=%ae|%an")
            for line in output.strip().split("\n"):
                if not line or "|" not in line:
                    continue
                email, name = line.split("|", 1)
                mapping[email.lower()].add(name)
        except subprocess.CalledProcessError:
            pass
        return dict(mapping)

    def _get_tags(self) -> list[tuple[str, str]]:
        """获取所有 tag 及其对应的提交 hash（按版本号降序）"""
        output = self._run_git(
            "tag", "-l", "--sort=-version:refname",
            "--format=%(refname:short) %(objectname)"
        )
        return [
            (parts[0], parts[1])
            for line in output.strip().split("\n")
            if line and len(parts := line.split()) == 2
        ]

    def _parse_commit(self, commit_line: str) -> Commit | None:
        """解析 git log 输出的单个提交"""
        parts = commit_line.split("|", 4)
        if len(parts) < 5:
            return None

        hash_val, author, email, date_str, message_full = parts

        # 过滤 merge commit
        first_line = message_full.strip().split("\n")[0]
        if first_line.startswith("Merge pull request"):
            return None

        date = self._parse_date(date_str)
        clean_message, footers = self._extract_footers(message_full)

        return Commit(
            hash=hash_val,
            message=clean_message,
            author=author,
            email=email,
            date=date,
            footers=footers,
        )

    def _parse_date(self, date_str: str) -> datetime:
        """解析日期字符串"""
        try:
            return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S %z")
        except ValueError:
            return datetime.now()

    def _extract_footers(self, message: str) -> tuple[str, dict[str, str]]:
        """从消息中提取 footer 并返回清理后的消息"""
        footers: dict[str, str] = {}
        clean_lines: list[str] = []

        for line in message.strip().split("\n"):
            stripped = line.strip()
            if stripped.startswith("Co-authored-by:") and ": " in stripped:
                key, value = stripped.split(": ", 1)
                footers[key] = value
            else:
                clean_lines.append(line)

        return "\n".join(clean_lines).strip(), footers

    def _filter_squash_commits(self, commits: list[Commit]) -> list[Commit]:
        """
        过滤和展开 squash merge 产生的提交
        
        策略:
        1. 检测 squash merge 提交(消息体中包含以 * 开头的子提交行)
        2. 将子提交行拆分为独立提交对象
        3. 保留原主提交的第一行
        4. 去重处理
        """
        result = []
        seen_messages = set()

        for commit in commits:
            # 使用原始完整消息来检测 squash 项
            lines = commit.original_message.strip().split("\n")
            first_line = lines[0].strip() if lines else ""

            # 检查是否是 squash merge: 消息体中有以 * 开头的子提交
            # 子提交格式: * type[emoji]: message (可能有空行)
            squash_items = []
            for line in lines[1:]:
                line_stripped = line.strip()
                if line_stripped.startswith("*") and ":" in line_stripped:
                    # 移除前导 * 和空白
                    squash_line = line_stripped.lstrip("* ").strip()
                    squash_items.append(squash_line)

            if squash_items:
                # 这是一个 squash merge,将其展开
                
                # 1. 添加主提交的第一行(但要去重,如果内容太相似则跳过)
                if first_line and first_line not in seen_messages:
                    seen_messages.add(first_line)
                    result.append(commit)

                # 2. 处理子提交
                for squash_line in squash_items:
                    # 如果已经出现过,跳过(去重)
                    if squash_line in seen_messages:
                        continue

                    seen_messages.add(squash_line)

                    # 创建虚拟的子提交对象
                    sub_commit = Commit(
                        hash=commit.hash,  # 使用父提交的hash
                        message=squash_line,
                        author=commit.author,
                        email=commit.email,
                        date=commit.date,
                        footers=commit.footers,
                        original_message=squash_line,
                    )
                    result.append(sub_commit)
            else:
                # 不是 squash merge,直接添加(如果未出现过)
                if first_line and first_line not in seen_messages:
                    seen_messages.add(first_line)
                    result.append(commit)

        return result

    def _group_commits(self, commits: list[Commit]) -> dict[str, list[Commit]]:
        """按提交类型分组并按优先级排序"""
        groups: dict[str, list[Commit]] = defaultdict(list)

        for commit in commits:
            group_name, _ = TYPE_GROUPS.get(commit.type, DEFAULT_GROUP)
            groups[group_name].append(commit)

        # 构建分组名到优先级的映射
        group_order = {v[0]: v[1] for v in TYPE_GROUPS.values()}
        return dict(
            sorted(groups.items(), key=lambda x: group_order.get(x[0], 99))
        )

    def get_commits_for_version(
        self, tag: str | None = None, previous_tag: str | None = None
    ) -> list[Commit]:
        """获取指定版本的提交"""
        # 构建 git log 范围
        if previous_tag and tag:
            range_spec = f"{previous_tag}..{tag}"
        elif previous_tag:
            range_spec = f"{previous_tag}..HEAD"
        elif tag:
            range_spec = tag
        else:
            range_spec = "HEAD"

        try:
            output = self._run_git(
                "log", range_spec,
                f"--format={GIT_LOG_FORMAT}{COMMIT_SEPARATOR}",
                "--no-merges",
            )
        except subprocess.CalledProcessError:
            return []

        commits = [
            commit
            for block in output.split(COMMIT_SEPARATOR)
            if block.strip()
            and (commit := self._parse_commit(self._clean_commit_block(block)))
        ]

        return self._filter_squash_commits(commits)

    def _clean_commit_block(self, block: str) -> str:
        """清理提交消息块，移除干扰行"""
        lines = block.strip().split("\n")
        cleaned: list[str] = []

        for i, line in enumerate(lines):
            # 前 4 行是 hash|author|email|date（消息从第 5 行开始）
            if i < 4:
                cleaned.append(line)
                continue

            stripped = line.strip()

            # 保留 squash merge 子提交（以 * 开头）
            if stripped.startswith("* "):
                cleaned.append(line)
                continue

            # 跳过分隔线
            if re.match(r"^-+$", stripped):
                continue

            # 跳过干扰文本
            if self._is_noise_line(stripped):
                continue

            cleaned.append(line)

        return "\n".join(cleaned)

    @staticmethod
    def _is_noise_line(line: str) -> bool:
        """判断是否是需要过滤的干扰行"""
        return any(pattern in line for pattern in NOISE_PATTERNS)

    def generate_version_section(
        self,
        version: str,
        date: datetime | None = None,
        commits: list[Commit] | None = None,
    ) -> str:
        """生成单个版本的 changelog 内容"""
        lines = [self._format_version_header(version, date)]

        if not commits:
            return "\n".join(lines)

        for group_name, group_commits in self._group_commits(commits).items():
            lines.append(f"### {group_name}\n")
            lines.extend(self._format_commit_group(group_commits))
            lines.append("")  # 组间空行

        return "\n".join(lines)

    def _format_version_header(self, version: str, date: datetime | None) -> str:
        """格式化版本标题"""
        if version == "unreleased":
            return "## 未发布\n"

        date_str = date.strftime("%Y-%m-%d") if date else ""
        version_clean = (
            version.replace("tags/", "").replace("refs/tags/", "").lstrip("v")
        )
        return f"## {version_clean} ({date_str})\n"

    def _format_commit_group(self, commits: list[Commit]) -> list[str]:
        """格式化一组提交为 changelog 条目"""
        lines: list[str] = []

        # 先显示有 scope 的提交（按 scope 排序）
        scoped = sorted((c for c in commits if c.scope), key=lambda x: x.scope)
        for commit in scoped:
            lines.append(self._format_commit_line(commit, with_scope=True))

        # 再显示无 scope 的提交
        for commit in commits:
            if not commit.scope:
                lines.append(self._format_commit_line(commit, with_scope=False))

        return lines

    def _format_commit_line(self, commit: Commit, with_scope: bool) -> str:
        """格式化单个提交条目"""
        msg = commit.get_display_message()
        author = self._get_author_mention(commit)
        if with_scope:
            return f"- *({commit.scope})* {msg} {author}"
        return f"- {msg} {author}"

    def _get_author_mention(self, commit: Commit) -> str:
        """获取 GitHub @提及格式

        策略:
        1. 如果能获取真实 GitHub username，使用 @username（会被渲染为链接）
        2. 如果无法获取，只使用昵称（不加 @，避免链接到错误用户）
        3. 如果有 Co-authored-by，添加到括号中
        """
        github_username = self.user_cache.get_github_username(
            commit.author, commit.email
        )

        # 只有确认是真实 GitHub 用户名时才使用 @ 前缀
        if github_username:
            mention = f"@{github_username}"
        else:
            # 无法确认时使用昵称，不加 @ 避免错误链接
            mention = commit.author

        if "Co-authored-by" in commit.footers:
            co_author = commit.footers["Co-authored-by"].split("<")[0].strip()
            return f"{mention} (Co-authored: {co_author})"

        return mention

    def generate_full_changelog(self, output_path: Path | None = None) -> str:
        """生成完整的 changelog"""
        lines = ["# 更新日志\n"]

        # 获取所有 tag
        tags = self._get_tags()

        # 添加未发布的提交
        if tags:
            latest_tag = tags[0][0]
            unreleased = self.get_commits_for_version(previous_tag=latest_tag)
            if unreleased:
                lines.append(self.generate_version_section("unreleased", commits=unreleased))

        # 为每个 tag 生成版本记录
        for i, (tag, tag_hash) in enumerate(tags):
            previous_tag = tags[i + 1][0] if i + 1 < len(tags) else None

            # 获取该版本的提交
            commits = self.get_commits_for_version(tag, previous_tag)

            # 获取 tag 的日期
            try:
                date_str = self._run_git(
                    "log", "-1", "--format=%ai", tag_hash
                ).strip()
                date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S %z")
            except (subprocess.CalledProcessError, ValueError):
                date = None

            section = self.generate_version_section(tag, date, commits)
            lines.append(section)

        changelog = "\n".join(lines)

        if output_path:
            output_path.write_text(changelog, encoding="utf-8")
            print(f"✅ Changelog 已生成: {output_path}")

        return changelog

    def generate_latest_version(self) -> str:
        """生成最新版本的 changelog"""
        tags = self._get_tags()
        if not tags:
            return "## 未发布\n\n(暂无发布版本)\n"

        latest_tag, tag_hash = tags[0]
        previous_tag = tags[1][0] if len(tags) > 1 else None

        commits = self.get_commits_for_version(latest_tag, previous_tag)

        try:
            date_str = self._run_git("log", "-1", "--format=%ai", tag_hash).strip()
            date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S %z")
        except (subprocess.CalledProcessError, ValueError):
            date = None

        return self.generate_version_section(latest_tag, date, commits)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="生成 CHANGELOG")
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("CHANGELOG.md"),
        help="输出文件路径",
    )
    parser.add_argument(
        "--latest",
        action="store_true",
        help="只生成最新版本",
    )
    parser.add_argument(
        "--repo",
        type=Path,
        help="Git 仓库路径(默认为当前目录)",
    )

    args = parser.parse_args()

    generator = ChangelogGenerator(args.repo)

    try:
        if args.latest:
            content = generator.generate_latest_version()
            print(content)
        else:
            generator.generate_full_changelog(args.output)

    except subprocess.CalledProcessError as e:
        print(f"❌ Git 命令执行失败: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ 生成失败: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
