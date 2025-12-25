# 生成 Changelog

本项目提供了两种生成 changelog 的方式。

## 主要特性

✨ **智能获取真实 GitHub 用户名** - 自动将 git 提交的用户信息转换为真实的 GitHub 用户名,确保 `@提及` 被正确识别

🚀 **完全自动化的用户名识别** - 无需任何手动配置,支持多种邮箱格式:

- GitHub 邮箱格式自动提取 (例如: `azmiao`, `dependabot[bot]`)
- 任意公开邮箱通过 API 查询 (需要 GITHUB_TOKEN)
- 邮箱 -> GitHub 账户的完整追踪

🐛 **完美处理 squash merge** - 自动展开并分类 squash merge 中的子提交列表

📋 **支持约定式提交格式** - 完整支持 conventional commits,包括 emoji 类型

---

## 方式一: Python 脚本(推荐)

使用 `scripts/generate_changelog.py` 脚本,提供更灵活的控制和自定义逻辑。

### 优点

- ✅ **灵活控制** - 可以按需解析 git log,自由过滤和分组
- ✅ **智能处理 squash merge** - 自动展开 squash merge 消息体中的子提交列表,各归其类
- ✅ **复杂逻辑处理** - 轻松处理多行消息、去重等场景
- ✅ **自定义格式** - 完全控制输出格式
- ✅ **易于调试** - 可以加日志、断点,查看中间状态
- ✅ **无外部依赖** - 只需 Python 标准库

### 使用方法

```bash
# 生成完整 changelog (本地自动提取 GitHub 邮箱格式的用户名)
python scripts/generate_changelog.py -o CHANGELOG.md

# 只查看最新版本
python scripts/generate_changelog.py --latest

# 指定仓库路径
python scripts/generate_changelog.py --repo /path/to/repo
```

**关键:**

- 脚本无需任何参数配置,开箱即用
- 对于使用 GitHub `noreply` 邮箱的用户,用户名会自动提取
- 对于使用公开邮箱的用户,需要设置 `GITHUB_TOKEN` 环境变量进行 API 查询

### 用户名获取策略

脚本采用完全自动化的策略获取 GitHub 用户名,无需任何手动配置:

1. **GitHub 邮箱格式提取** (最高优先级,自动)
   - 当用户用 GitHub 提供的 `noreply` 邮箱时自动提取
   - 格式: `{id}+{username}@users.noreply.github.com`
   - 例如: `54100327+azmiao@users.noreply.github.com` -> 自动提取 `azmiao`
   - 无需任何配置,立即生效

2. **GitHub API 查询** (自动,需要 token)
   - 当用户用公开邮箱(如 `outlook.com`, `gmail.com` 等)时通过 API 查询
   - 使用 `GITHUB_TOKEN` 环境变量 (GitHub Actions 自动提供)
   - 脚本会查询邮箱对应的 GitHub 账户名
   - 结果被缓存以提高性能

3. **昵称回退** (无法识别时)
   - 当无法通过上述方式识别时,使用原始 git 提交中的昵称
   - 这种情况下 `@提及` 可能无法被 GitHub 识别

### 工作原理

1. **读取 git 历史** - 使用 `git log` 获取提交记录
2. **解析提交** - 按约定式提交格式解析 type、scope、message,支持带 emoji 的格式
3. **获取用户名** - 自动识别 GitHub 用户名 (GitHub 邮箱格式提取或 API 查询)
4. **展开 squash merge** - 检测并展开消息体中的 `*` 开头的子提交行
5. **过滤干扰** - 移除 dependabot 样板文本、分隔线等
6. **分组排序** - 按提交类型分组,组内按 scope 排序
7. **格式化输出** - 生成 Markdown 格式的 changelog,使用真实 GitHub 用户名创建提及链接

### squash merge 处理

脚本会自动检测 squash merge 提交(消息体包含 `*` 开头的行),并将这些子提交展开:

**原始提交消息:**

```text
tag📌: v0.5.8 (#57)

* feat✨: 合并补充广告关闭
* fix🐛: 修复 Release Note 的问题
* perf👌: 优化初始化逻辑
```

**生成的 changelog:**

```text
### ✨ 新功能
- 合并补充广告关闭 @author

### 🐛 Bug修复
- 修复 Release Note 的问题 @author

### 🚀 性能优化
- 优化初始化逻辑 @author

### 📌 发布
- v0.5.8 (#57) @author
```

### 支持的提交类型

| Type | 分组 | 说明 |
|------|------|------|
| `feat` | ✨ 新功能 | 新增功能 |
| `fix`, `patch` | 🐛 Bug修复 | 修复bug |
| `perf` | 🚀 性能优化 | 性能改进 |
| `refactor` | 🎨 代码重构 | 重构代码 |
| `format` | 🥚 格式化 | 代码格式化 |
| `style` | 💄 样式 | 样式调整 |
| `docs` | 📚 文档 | 文档更新 |
| `chore`, `git` | 🧹 日常维护 | 日常维护 |
| `deps`, `build` | 🧩 修改依赖 | 依赖更新 |
| `revert` | 🔁 还原提交 | 回退提交 |
| `test` | 🧪 测试 | 测试相关 |
| `file` | 📦 文件变更 | 文件操作 |
| `tag` | 📌 发布 | 版本发布 |
| `config` | 🔧 配置文件 | 配置修改 |
| `ci` | ⚙️ 持续集成 | CI/CD |
| `init` | 🎉 初始化 | 项目初始化 |
| `wip` | 🚧 进行中 | 进行中的功能 |

### 自动过滤

脚本会自动过滤以下内容:

- ❌ Merge pull request 提交
- ❌ Dependabot 的样板描述文本
- ❌ 分隔线 (`---`, `------` 等)
- ❌ `Signed-off-by` 行
- ✅ 展开并分类 squash merge 的子提交(`*` 开头)
- ✅ 保留 `Co-authored-by` 作为 footer 显示

### 自定义脚本

如果需要修改 changelog 格式或逻辑,直接编辑 `scripts/generate_changelog.py`:

```python
# 修改分组标题
TYPE_GROUPS = {
    "feat": ("✨ Features", 0),  # 改为英文
    # ...
}

# 修改提交显示格式
def get_display_message(self) -> str:
    # 自定义消息格式
    return f"[{self.type}] {self.message}"

# 修改 squash 展开逻辑
def _filter_squash_commits(self, commits):
    # 自定义 squash 处理
    pass
```

---

## 方式二: git-cliff(配置较复杂)

使用 `git-cliff` 工具和 `.github/cliff.toml` 配置文件。

### 优点

- ✅ 专业工具,社区广泛使用
- ✅ 支持多种输出格式

### 缺点

- ⚠️ 配置复杂,难以调试
- ⚠️ 模板语法限制较多
- ⚠️ 处理复杂场景(squash merge)需要大量正则和预处理器

### 使用方法

```bash
# 安装 git-cliff
cargo install git-cliff

# 生成完整 changelog
git cliff -c .github/cliff.toml --strip header -o CHANGELOG.md

# 只生成最新版本
git cliff -c .github/cliff.toml --latest --strip header
```

---

## 推荐工作流

### 日常开发

使用 Python 脚本快速查看:

```bash
python scripts/generate_changelog.py --latest
```

### 发版前

生成完整 changelog:

```bash
python scripts/generate_changelog.py -o CHANGELOG.md
git add CHANGELOG.md
git commit -m "docs📚: 更新 CHANGELOG"
```

### CI/CD 集成

在 GitHub Actions 中自动生成,脚本会自动使用 `GITHUB_TOKEN`:

**生成 Release Body (最新版本):**

```yaml
changelog:
  name: Generate changelog
  runs-on: ubuntu-latest
  outputs:
    release_body: ${{ steps.generate-changelog.outputs.content }}
  steps:
    - name: Checkout
      uses: actions/checkout@v6
      with:
        fetch-depth: 0

    - name: Setup Python
      uses: actions/setup-python@v6
      with:
        python-version: '3.13'

    - name: Generate changelog with Python script
      id: generate-changelog
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      run: |
        # 生成最新版本的 changelog
        python scripts/generate_changelog.py --latest > CHANGES.md
        
        # 将内容输出到 GitHub Actions output
        {
          echo 'content<<EOF'
          cat CHANGES.md
          echo EOF
        } >> "$GITHUB_OUTPUT"
        
        echo "✅ Changelog 已生成"
```

**生成完整 CHANGELOG.md:**

```yaml
- name: Generate full CHANGELOG
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
  run: |
    python scripts/generate_changelog.py -o CHANGELOG.md
    
- name: Commit changelog
  run: |
    git add CHANGELOG.md
    git config --local user.email "action@github.com"
    git config --local user.name "GitHub Action"
    git commit -m "docs📚: 更新 CHANGELOG" || echo "No changes to commit"
```

**关键点:**

- `GITHUB_TOKEN` 会被 GitHub Actions 自动设置,脚本无需任何特殊配置
- 脚本会自动用 token 查询公开邮箱对应的 GitHub 用户名
- 生成的 changelog 中的 `@提及` 会被正确链接到对应用户
- 使用 `--latest` 参数生成最新版本（适用于 Release Body）
- 不带参数或使用 `-o` 生成完整的 CHANGELOG.md 文件---

## 常见问题

### Q: 为什么 `@233` 没有被转换为 `@233Official`?

A: 脚本有以下几种方式可以识别 `233` 用户的真实 GitHub 用户名:

1. **本地环境已配置 `GITHUB_TOKEN`**
   - 如果本地已有有效的 GitHub token,脚本会自动查询邮箱对应的 GitHub 用户名
   - 验证方法: `echo $GITHUB_TOKEN` 查看是否设置

2. **CI/CD 环境中自动处理**
   - GitHub Actions 会自动提供 `GITHUB_TOKEN` 环境变量
   - 脚本无需任何配置,会自动查询所有公开邮箱对应的用户名

3. **本地测试时(无 token)**
   - 如果本地没有 token,公开邮箱用户会显示为昵称 (例如 `@233`)
   - 这时可以在 CI/CD 中生成 changelog,会自动获取真实用户名

### Q: 为什么 squash merge 的子提交没有被展开?

A: 确保:

1. squash merge 的子提交格式正确: `* type: message`
2. 每条子提交前面有 `*` 符号
3. 使用了最新的脚本版本

### Q: 如何添加新的提交类型?

A: 编辑 `scripts/generate_changelog.py` 中的 `TYPE_GROUPS` 字典:

```python
TYPE_GROUPS = {
    # ...
    "wip": ("🚧 进行中", 17),  # 新增
}
```

### Q: 如何修改日期格式?

A: 修改 `generate_version_section` 方法中的 `strftime` 格式:

```python
date_str = date.strftime("%Y年%m月%d日")  # 改为中文
```

### Q: squash merge 的消息体行数太多会不会有问题?

A: 不会!脚本可以处理任意数量的子提交行,会逐条展开。

### Q: 如何跳过某个提交类型?

A: 修改 `TYPE_GROUPS`,或在 `_filter_squash_commits` 中添加过滤逻辑。

---

## 贡献

如果你发现 changelog 生成有问题或有改进建议,欢迎:

1. 提 Issue
2. 提交 PR 改进脚本
3. 在讨论区分享你的用法
