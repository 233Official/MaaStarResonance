<#
 .SYNOPSIS
  本地（仅 Windows x86_64）创建一个新的版本发布目录并打包产物。

 .DESCRIPTION
  - 不依赖 GitHub Actions / 远程托管，仅在本机使用。
  - 版本号格式: v<major>.<minor>.<patch> 例如 v0.1.3
  - 自动扫描 `releases/` 下既有目录 (vX.X.X) 计算下一个版本，或用参数覆盖。
  - 调用 `install.py <version>` 生成 `install/` 目录，然后打包 zip 到对应发布目录。
  - 生成 metadata (release.json) + SHA256 校验文件。
  - 可指定升级类型 (patch|minor|major) 或直接传入 --Version。

 .PARAMETER Bump
  指定语义化版本递增维度：patch (默认) | minor | major。

 .PARAMETER Version
  直接指定完整版本号（含 v 前缀）。若提供则忽略 Bump。

 .PARAMETER Force
  允许指定版本号 <= 当前最高版本（覆盖风险自担）。

 .PARAMETER SkipBuild
  跳过运行 install.py，仅重新打包当前已有的 install/ 目录。

 .PARAMETER SkipMfaMerge
  如果你的 install.py 之外还有手动合并 MFAAvalonia 的步骤且想跳过，可加此参数（脚本目前只保留占位）。

 .PARAMETER PythonExe
  指定 Python 可执行文件路径，默认自动查找 `python`。

 .EXAMPLE
  ./scripts/new-release.ps1            # 计算下一 patch 版本并生成

 .EXAMPLE
  ./scripts/new-release.ps1 -Bump minor

 .EXAMPLE
  ./scripts/new-release.ps1 -Version v1.2.0

 .NOTES
  仅面向 Windows PowerShell / pwsh。请在仓库根目录执行。
#>
param(
    [ValidateSet('patch','minor','major')] [string]$Bump = 'patch',
    [string]$Version,
    [switch]$Force,
    [switch]$SkipBuild,
    [switch]$SkipMfaMerge,
    [switch]$SkipDeps,               # 跳过依赖(MaaFramework / MFAAvalonia)下载
    [string]$PythonExe = 'python',
    [string]$GitHubToken,            # 可选：提升 API 速率限制
    [switch]$KeepArchives             # 保留下载的压缩包
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Section($msg){ Write-Host "`n=== $msg ===" -ForegroundColor Cyan }
function Fail($msg){ Write-Error $msg; exit 1 }
function Warn($msg){ Write-Warning $msg }

# 确定仓库根（脚本所在目录的上级或上上级）
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Resolve-Path (Join-Path $ScriptDir '..')) | Out-Null
$RepoRoot = Get-Location

$ReleasesDir = Join-Path $RepoRoot 'releases'
if (!(Test-Path $ReleasesDir)) { New-Item -ItemType Directory -Path $ReleasesDir | Out-Null }

# 依赖下载目录
$DepsDir = Join-Path $RepoRoot 'deps'
if (!(Test-Path $DepsDir)) { New-Item -ItemType Directory -Path $DepsDir | Out-Null }
$MfaDir = Join-Path $RepoRoot 'MFA'
if (!(Test-Path $MfaDir)) { New-Item -ItemType Directory -Path $MfaDir | Out-Null }

function Get-ExistingVersions {
    Get-ChildItem -Path $ReleasesDir -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match '^v\d+\.\d+\.\d+$' } |
        ForEach-Object {
            [PSCustomObject]@{ Name = $_.Name; Version = [version]($_.Name.TrimStart('v')) }
        } | Sort-Object Version
}

function Compute-NextVersion($latestVersion,[string]$bump){
    if(-not $latestVersion){ return [version]'0.0.0' } # 初始基线，再在后面 bump
    switch($bump){
        'major' { return [version]::new($latestVersion.Major + 1,0,0) }
        'minor' { return [version]::new($latestVersion.Major,$latestVersion.Minor + 1,0) }
        default { return [version]::new($latestVersion.Major,$latestVersion.Minor,$latestVersion.Build + 1) }
    }
}

Write-Section '解析现有版本'
$existing = Get-ExistingVersions
$latest = $existing | Select-Object -Last 1
if($latest){ Write-Host ("最新版本: v{0}" -f $latest.Version) } else { Write-Host '尚无历史版本（将从 v0.0.0 开始）' }

if($Version){
    if($Version -notmatch '^v\d+\.\d+\.\d+$'){ Fail 'Version 必须形如 v1.2.3' }
    $targetVersion = [version]($Version.TrimStart('v'))
} else {
    $targetVersion = Compute-NextVersion $latest.Version $Bump
}

if($latest -and $targetVersion -le $latest.Version -and -not $Force){
    Fail "指定目标版本 v$targetVersion <= 当前最新版本 v$($latest.Version)。若要强制请加 -Force"
}

$VersionTag = 'v' + $targetVersion.ToString()
Write-Host "目标版本: $VersionTag" -ForegroundColor Green

$ReleaseDir = Join-Path $ReleasesDir $VersionTag
if(Test-Path $ReleaseDir){ if(-not $Force){ Fail "发布目录已存在: $ReleaseDir (可用 -Force 覆盖)" } else { Write-Host '覆盖已有发布目录' -ForegroundColor Yellow } }
New-Item -ItemType Directory -Force -Path $ReleaseDir | Out-Null

# --------------------------- 下载依赖 (可选) ---------------------------
function Invoke-GitHubApi {
    param(
        [string]$Url
    )
    $headers = @{ 'User-Agent' = 'local-release-script' }
    if($GitHubToken){ $headers.Authorization = "Bearer $GitHubToken" }
    try {
        return Invoke-RestMethod -Uri $Url -Headers $headers -ErrorAction Stop
    } catch {
        Fail "GitHub API 调用失败: $Url => $($_.Exception.Message)"
    }
}

function Download-Asset {
    param(
        [string]$DownloadUrl,
        [string]$OutFile
    )
    $headers = @{ 'User-Agent' = 'local-release-script' }
    if($GitHubToken){ $headers.Authorization = "Bearer $GitHubToken" }
    Write-Host "下载: $DownloadUrl -> $OutFile"
    try {
        Invoke-WebRequest -Uri $DownloadUrl -Headers $headers -OutFile $OutFile -UseBasicParsing -ErrorAction Stop
    } catch {
        Fail "下载失败: $($_.Exception.Message)"
    }
}

function Get-LatestReleaseAssets {
    param([string]$Repo)
    $api = "https://api.github.com/repos/$Repo/releases/latest"
    $json = Invoke-GitHubApi -Url $api
    if(-not $json.assets){ Fail "未在 $Repo 最新发布中找到 assets" }
    return $json.assets
}

function Find-AssetByPattern {
    param(
        [array]$Assets,
        [string]$Pattern
    )
    # Pattern 为简单通配 ( * 匹配任意 )，转为正则
    $regex = '^' + [Regex]::Escape($Pattern).Replace('\*','.*') + '$'
    return $Assets | Where-Object { $_.name -match $regex } | Select-Object -First 1
}

if(-not $SkipDeps){
    Write-Section '下载 MaaFramework (win x86_64)'
    $maaAssets = Get-LatestReleaseAssets -Repo 'MaaXYZ/MaaFramework'
    $maaPattern = 'MAA-win-x86_64*'
    $maaAsset = Find-AssetByPattern -Assets $maaAssets -Pattern $maaPattern
    if(-not $maaAsset){ Fail "未找到匹配 $maaPattern 的 MaaFramework 资源" }
    $maaOut = Join-Path $DepsDir $maaAsset.name
    if(!(Test-Path $maaOut)){ Download-Asset -DownloadUrl $maaAsset.browser_download_url -OutFile $maaOut }
    if($maaOut -match '\.zip$'){
        Write-Host '解压 MaaFramework ...'
        Expand-Archive -Path $maaOut -DestinationPath $DepsDir -Force
        if(-not $KeepArchives){ Remove-Item $maaOut -Force }
    } else {
        Write-Host 'MaaFramework 资源不是 zip，跳过解压'
    }

    Write-Section '下载 MFAAvalonia (win x64)'
    $mfaAssets = Get-LatestReleaseAssets -Repo 'SweetSmellFox/MFAAvalonia'
    $mfaPattern = 'MFAAvalonia-*-win-x64*'
    $mfaAsset = Find-AssetByPattern -Assets $mfaAssets -Pattern $mfaPattern
    if($mfaAsset){
        $mfaOut = Join-Path $MfaDir $mfaAsset.name
        if(!(Test-Path $mfaOut)){ Download-Asset -DownloadUrl $mfaAsset.browser_download_url -OutFile $mfaOut }
        if($mfaOut -match '\.zip$'){
            Write-Host '解压 MFAAvalonia ...'
            Expand-Archive -Path $mfaOut -DestinationPath $MfaDir -Force
            if(-not $KeepArchives){ Remove-Item $mfaOut -Force }
        }
    } else {
        Warn "未找到匹配 $mfaPattern 的 MFAAvalonia 资源（将继续）"
    }
} else {
    Write-Section '跳过依赖下载'
}

# 记录当前 Git 信息（如果有）
function Get-GitMeta {
    $meta = [ordered]@{}
    try { $meta.Branch = (git rev-parse --abbrev-ref HEAD 2>$null) } catch {}
    try { $meta.Commit = (git rev-parse --short HEAD 2>$null) } catch {}
    try { $meta.StatusClean = ((git status --porcelain 2>$null).Length -eq 0) } catch {}
    return $meta
}
$GitMeta = Get-GitMeta

if(-not $SkipBuild){
    Write-Section '执行安装脚本 (install.py)'
    $pyCmd = "$PythonExe install.py $VersionTag"
    Write-Host "运行: $pyCmd"
    & $PythonExe install.py $VersionTag
    if($LASTEXITCODE -ne 0){ Fail "install.py 执行失败，退出码 $LASTEXITCODE" }
} else {
    Write-Section '跳过构建 (使用现有 install/ 目录)'
}

if(!(Test-Path (Join-Path $RepoRoot 'install'))){ Fail '未找到 install/ 目录，无法继续打包。' }

# TODO: 如需合并 MFA，可在此加入实际逻辑（目前只在 Actions 中处理）。
if(-not $SkipMfaMerge){
    Write-Section '合并 MFAAvalonia 文件'
    if(Test-Path $MfaDir){
        if(Test-Path (Join-Path $MfaDir 'install')){
            # 某些包可能自带 install 目录结构
            $source = Join-Path $MfaDir 'install'
            Write-Host "检测到嵌套 install 目录: $source"
        } else {
            $source = $MfaDir
        }
        Write-Host "拷贝 $source -> install/ (忽略已存在)"
        robocopy $source (Join-Path $RepoRoot 'install') /E /NFL /NDL /NJH /NJS /NP /XO | Out-Null
    } else {
        Write-Host 'MFA 目录不存在，跳过。'
    }
}

Write-Section '打包产物'
$ArtifactName = "MaaStarResonance-win-x86_64-$VersionTag.zip"
$ArtifactPath = Join-Path $ReleaseDir $ArtifactName
if(Test-Path $ArtifactPath){ Remove-Item $ArtifactPath -Force }
Compress-Archive -Path (Join-Path $RepoRoot 'install' '*') -DestinationPath $ArtifactPath -Force

Write-Host "产物: $ArtifactPath" -ForegroundColor Green

Write-Section '生成校验值'
$hash = Get-FileHash -Algorithm SHA256 $ArtifactPath
$hashLine = "$($hash.Hash)  $ArtifactName"
Set-Content -Path (Join-Path $ReleaseDir 'SHA256SUMS.txt') -Value $hashLine -Encoding UTF8

Write-Section '生成 metadata'
$Metadata = [ordered]@{
  version = $VersionTag
  created_at = (Get-Date).ToString('s')
  artifact = $ArtifactName
  sha256 = $hash.Hash
  bump = $Bump
  skip_build = [bool]$SkipBuild
  git = $GitMeta
}
$Metadata | ConvertTo-Json -Depth 6 | Set-Content -Encoding UTF8 (Join-Path $ReleaseDir 'release.json')

# 从 CHANGLOG / CHANGELOG 中抽取该版本条目 (简单策略：读取前 200 行)
$ChangelogCandidates = @('CHANGELOG.md','CHANGLOG.md') | Where-Object { Test-Path (Join-Path $RepoRoot $_) }
if($ChangelogCandidates){
    # 处理单个字符串被当作字符数组的问题，统一用 Select-Object -First 1
    $clFileName = ($ChangelogCandidates | Select-Object -First 1)
    $clFile = Join-Path $RepoRoot $clFileName
    try {
        $clTop = Get-Content -Path $clFile -TotalCount 200 -ErrorAction Stop
        Set-Content -Path (Join-Path $ReleaseDir 'CHANGELOG.snippet.txt') -Value $clTop -Encoding UTF8
    } catch {
        Write-Warning "读取 CHANGELOG 失败: $($_.Exception.Message)"
    }
}

Write-Section '完成'
Write-Host "新版本已创建: $VersionTag" -ForegroundColor Green
Write-Host "目录: $ReleaseDir"
Write-Host '下一步：可手动签名 / 上传 / 备份该产物。'
