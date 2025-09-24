# 计算下一 patch 版本 (基于 releases/ 下已有 vX.X.X)
pwsh ./scripts/new-release.ps1

# 指定语义递增：minor / major
pwsh ./scripts/new-release.ps1 -Bump minor
pwsh ./scripts/new-release.ps1 -Bump major

# 直接指定版本号
pwsh ./scripts/new-release.ps1 -Version v0.4.0

# 强制覆盖已存在版本目录
pwsh ./scripts/new-release.ps1 -Version v0.4.0 -Force

# 跳过重新执行 install.py（仅重新打包当前 install/）
pwsh ./scripts/new-release.ps1 -SkipBuild

# 指定 Python 可执行
pwsh ./scripts/new-release.ps1 -PythonExe 'C:\\Python312\\python.exe'


# 自动计算下一 patch 版本并下载依赖、构建、打包
pwsh ./scripts/new-release.ps1

# 指定版本 + 保留压缩包 + 使用 Token
pwsh ./scripts/new-release.ps1 -Version v0.0.5 -GitHubToken $env:GITHUB_TOKEN -KeepArchives

# 仅重新打包（不重新构建、不重新下载）
pwsh ./scripts/new-release.ps1 -Version v0.0.5 -Force -SkipBuild -SkipDeps