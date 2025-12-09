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

import os
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.request import Request, urlopen
from urllib.error import URLError
import json


@dataclass
class Commit:
    """提交信息"""

    hash: str
    message: str
    author: str
    email: str
    date: datetime
    type: str = ""
    scope: str = ""
    breaking: bool = False
    footers: dict = field(default_factory=dict)
    # 保存原始完整消息用于 squash 处理
    original_message: str = ""
    # 缓存的 GitHub 用户 ID
    github_id: Optional[int] = None

    def __post_init__(self):
        # 保存原始消息(包含所有行)
        if not self.original_message:
            self.original_message = self.message
        self._parse_message()

    def _parse_message(self):
        """解析约定式提交消息"""
        lines = self.message.strip().split("\n")
        if not lines:
            return

        # 解析第一行: type(scope): message 或 type: message 或 type🎨: message
        first_line = lines[0].strip()

        # 移除可能的前导符号 (-, *, 等)
        first_line = re.sub(r"^[-*]\s*", "", first_line)

        # 匹配约定式提交格式 (支持 emoji)
        # 匹配模式: type[emoji](scope): message 或 type[emoji]: message
        match = re.match(
            r"^(?P<type>\w+)(?P<emoji>[^\w\s:(]*)?(?:\((?P<scope>[^)]+)\))?\s*:\s*(?P<message>.+)$",
            first_line,
        )

        if match:
            self.type = match.group("type").lower()
            self.scope = match.group("scope") or ""
            # 保留原始消息(不含type/emoji/scope前缀)
            self.message = match.group("message").strip()
        else:
            # 特殊处理 Revert 提交
            if first_line.lower().startswith("revert"):
                self.type = "revert"
                self.message = first_line
            else:
                # 特殊提交类型 (如 WIP、docs update 等)
                # 尝试提取 emoji 后的文本
                emoji_match = re.match(r"^(\w+)([^:]*?):\s*(.+)$", first_line)
                if emoji_match:
                    self.type = emoji_match.group(1).lower()
                    self.message = emoji_match.group(3).strip()
                else:
                    # 无法解析,归类为 chore
                    self.type = "chore"
                    self.message = first_line

        # 解析 footer (Co-authored-by 等)
        for line in lines[1:]:
            line = line.strip()
            if ": " in line:
                key, value = line.split(": ", 1)
                if key in ["Co-authored-by", "Signed-off-by"]:
                    self.footers[key] = value

    def get_display_message(self) -> str:
        """获取用于显示的消息(第一行)"""
        return self.message.split("\n")[0].strip()

    def get_author_display(self) -> str:
        """获取作者显示名称"""
        # 如果有 Co-authored-by,也显示出来
        if "Co-authored-by" in self.footers:
            co_author = self.footers["Co-authored-by"].split("<")[0].strip()
            return f"@{self.author} (Co-authored: {co_author})"
        return f"@{self.author}"


class GitHubUserCache:
    """GitHub 用户名缓存与获取"""

    def __init__(self, email_to_names: Optional[dict[str, set[str]]] = None):
        self.cache: dict[str, Optional[str]] = {}
        self.github_token = os.getenv("GITHUB_TOKEN")
        # 邮箱到用户名的映射(用于反向查询)
        self.email_to_names = email_to_names or {}

    def get_github_username(self, author_name: str, author_email: str) -> Optional[str]:
        """获取用户的真实 GitHub 用户名
        
        策略:
        1. 从邮箱中提取 (GitHub 邮箱格式)
        2. 通过 GitHub API 查询邮箱对应的用户名
        3. 返回原始作者名 (作为回退)
        """
        if not author_name:
            return None

        # 检查缓存 (key 包含邮箱,保证不同邮箱的同一昵称能被区分)
        cache_key = f"{author_name}|{author_email}"
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            return cached if cached else None

        # 策略 1: 从邮箱中提取 GitHub 用户名
        # GitHub 生成的邮箱格式: {id}+{username}@users.noreply.github.com
        if author_email and "users.noreply.github.com" in author_email:
            username = self._extract_username_from_github_email(author_email)
            if username:
                self.cache[cache_key] = username
                return username

        # 策略 2: 通过 GitHub API 查询邮箱对应的用户
        # 这是解决非标准邮箱用户名识别的最可靠方式
        if self.github_token:
            username = self._fetch_username_by_email(author_email)
            if username:
                self.cache[cache_key] = username
                return username

        # 策略 3: 缓存回退结果
        self.cache[cache_key] = None
        return None

    def _extract_username_from_github_email(self, email: str) -> Optional[str]:
        """从 GitHub 生成的邮箱中提取 username
        
        格式: {id}+{username}@users.noreply.github.com
        例如: 2475613+azmiao@users.noreply.github.com -> azmiao
        """
        if not email or "@users.noreply.github.com" not in email:
            return None

        try:
            # 提取 @ 前的部分
            local_part = email.split("@")[0]
            # 提取 + 后的部分
            if "+" in local_part:
                username = local_part.split("+", 1)[1]
                return username if username else None
        except (IndexError, ValueError):
            pass

        return None

    def _fetch_username_by_email(self, email: str) -> Optional[str]:
        """通过 GitHub API 查询邮箱对应的用户名
        
        策略:
        1. 直接用邮箱搜索
        2. 如果失败,尝试用关联的用户名去搜 (从 git 历史中获取)
        3. 返回找到的第一个有效用户名
        """
        if not email or not self.github_token:
            return None

        # 首先尝试直接用邮箱搜索
        username = self._search_github_by_email(email)
        if username:
            return username

        # 如果邮箱搜索失败,尝试用关联的用户名搜索
        email_lower = email.lower()
        if email_lower in self.email_to_names:
            for name in self.email_to_names[email_lower]:
                username = self._search_github_by_username(name)
                if username:
                    return username

        return None

    def _search_github_by_email(self, email: str) -> Optional[str]:
        """通过邮箱搜索 GitHub 用户"""
        try:
            url = f"https://api.github.com/search/users?q={email}+in:email"
            headers = {
                "Authorization": f"token {self.github_token}",
                "Accept": "application/vnd.github.v3+json",
            }

            req = Request(url, headers=headers)
            with urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                items = data.get("items", [])

                if items:
                    # 返回第一个匹配的用户名
                    username = items[0].get("login")
                    return username
        except (URLError, json.JSONDecodeError, KeyError, Exception):
            pass

        return None

    def _search_github_by_username(self, username: str) -> Optional[str]:
        """通过用户名直接查询 GitHub API (验证用户是否存在)"""
        try:
            url = f"https://api.github.com/users/{username}"
            headers = {
                "Authorization": f"token {self.github_token}",
                "Accept": "application/vnd.github.v3+json",
            }

            req = Request(url, headers=headers)
            with urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                # 返回 API 返回的用户名 (规范化)
                login = data.get("login")
                return login
        except (URLError, json.JSONDecodeError, KeyError, Exception):
            pass

        return None


class ChangelogGenerator:
    """Changelog 生成器"""

    # 提交类型到分组的映射
    TYPE_GROUPS = {
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

    def __init__(self, repo_path: Optional[Path] = None):
        self.repo_path = repo_path or Path.cwd()
        # 构建邮箱 -> 用户名的映射(用于反向查询)
        self.email_to_names = self._build_email_to_names_map()
        # 传递给 cache 使用
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
        """获取所有 tag 及其对应的提交hash"""
        output = self._run_git("tag", "-l", "--sort=-version:refname", "--format=%(refname:short) %(objectname)")
        tags = []
        for line in output.strip().split("\n"):
            if not line:
                continue
            parts = line.split()
            if len(parts) == 2:
                tags.append((parts[0], parts[1]))
        return tags  # 已经按版本号降序排序

    def _parse_commit(self, commit_line: str) -> Optional[Commit]:
        """解析 git log 输出的一行"""
        # 格式: hash|author|email|date|message
        parts = commit_line.split("|", 4)
        if len(parts) < 5:
            return None

        hash_val, author, email, date_str, message_full = parts

        # 过滤明显的 merge commit
        first_line = message_full.strip().split("\n")[0]
        if first_line.startswith("Merge pull request"):
            return None

        # 解析日期
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S %z")
        except ValueError:
            date = datetime.now()

        # 提取 footers (在消息最后)
        footers = {}
        message_lines = message_full.strip().split("\n")
        clean_message_lines = []
        
        for line in message_lines:
            # 检查是否是 footer (只提取 Co-authored-by, 其他的保留)
            if line.strip().startswith("Co-authored-by:") and ": " in line:
                key, value = line.split(": ", 1)
                footers[key.strip()] = value.strip()
            else:
                clean_message_lines.append(line)
        
        clean_message = "\n".join(clean_message_lines).strip()

        return Commit(
            hash=hash_val,
            message=clean_message,
            author=author,
            email=email,
            date=date,
            footers=footers,
        )

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
        """按类型分组提交"""
        groups = defaultdict(list)

        for commit in commits:
            group_name, order = self.TYPE_GROUPS.get(
                commit.type, ("其他变更", 99)
            )
            groups[group_name].append(commit)

        # 按优先级排序
        return dict(
            sorted(
                groups.items(),
                key=lambda x: next(
                    (v[1] for k, v in self.TYPE_GROUPS.items() if v[0] == x[0]),
                    99,
                ),
            )
        )

    def get_commits_for_version(
        self, tag: Optional[str] = None, previous_tag: Optional[str] = None
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

        # 获取提交
        format_str = "%H|%an|%ae|%ai|%B"
        separator = "---COMMIT-SEPARATOR---"

        try:
            output = self._run_git(
                "log",
                range_spec,
                f"--format={format_str}{separator}",
                "--no-merges",
            )
        except subprocess.CalledProcessError:
            return []

        commits = []
        for commit_block in output.split(separator):
            if not commit_block.strip():
                continue

            # 移除消息体中的干扰行
            lines = commit_block.strip().split("\n")
            cleaned_lines = []
            in_message = False
            message_start_idx = 0

            for i, line in enumerate(lines):
                # 前4行是 hash|author|email|date
                if i < 4:
                    cleaned_lines.append(line)
                    if i == 3:
                        message_start_idx = len(cleaned_lines)
                        in_message = True
                else:
                    # 过滤消息体中的干扰行
                    line_stripped = line.strip()

                    # 保留 squash merge 的子提交列表 (以 * 开头) - 后续处理
                    if line_stripped.startswith("* "):
                        cleaned_lines.append(line)
                        continue

                    # 跳过分隔线
                    if re.match(r"^-+$", line_stripped):
                        continue

                    # 跳过 dependabot 样板文本
                    if any(
                        pattern in line_stripped
                        for pattern in [
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
                    ):
                        continue

                    cleaned_lines.append(line)

            cleaned_block = "\n".join(cleaned_lines)

            commit = self._parse_commit(cleaned_block)
            if commit:
                commits.append(commit)

        return self._filter_squash_commits(commits)

    def generate_version_section(
        self,
        version: str,
        date: Optional[datetime] = None,
        commits: Optional[list[Commit]] = None,
    ) -> str:
        """生成单个版本的 changelog 内容"""
        lines = []

        # 版本标题
        if version == "unreleased":
            lines.append("## 未发布\n")
        else:
            date_str = date.strftime("%Y-%m-%d") if date else ""
            # 清理版本号: 移除 tags/ refs/tags/ 等前缀
            version_clean = version.replace("tags/", "").replace("refs/tags/", "").lstrip("v")
            lines.append(f"## {version_clean} ({date_str})\n")

        if not commits:
            return "\n".join(lines)

        # 按类型分组
        grouped = self._group_commits(commits)

        for group_name, group_commits in grouped.items():
            lines.append(f"### {group_name}\n")

            # 先显示有 scope 的提交(按 scope 排序)
            scoped = sorted(
                [c for c in group_commits if c.scope],
                key=lambda x: x.scope,
            )
            for commit in scoped:
                msg = commit.get_display_message()
                author_display = self._get_author_mention(commit)
                lines.append(f"- *({commit.scope})* {msg} {author_display}")

            # 再显示无 scope 的提交
            unscoped = [c for c in group_commits if not c.scope]
            for commit in unscoped:
                msg = commit.get_display_message()
                author_display = self._get_author_mention(commit)
                lines.append(f"- {msg} {author_display}")

            lines.append("")  # 组之间空一行

        return "\n".join(lines)

    def _get_author_mention(self, commit: Commit) -> str:
        """获取 GitHub @提及格式
        
        优先级:
        1. 如果有真实 GitHub username,使用 @username
        2. 否则使用原始昵称 @nickname
        3. 如果有 Co-authored-by,添加到括号中
        """
        # 获取真实的 GitHub username
        github_username = self.user_cache.get_github_username(commit.author, commit.email)
        
        if github_username:
            author_mention = f"@{github_username}"
        else:
            # 无法获取真实用户名时,使用昵称
            author_mention = f"@{commit.author}"

        # 添加 Co-authored-by 信息
        if "Co-authored-by" in commit.footers:
            co_author = commit.footers["Co-authored-by"].split("<")[0].strip()
            return f"{author_mention} (Co-authored: {co_author})"

        return author_mention

    def generate_full_changelog(self, output_path: Optional[Path] = None) -> str:
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
