# Windows bootstrap. Use: & ([scriptblock]::Create((irm <public installer URL>)))
[CmdletBinding()]
param(
    [string]$Dest = "",
    [switch]$SkipSystemDeps,
    [switch]$NoSmoke,
    [switch]$DryRun
)
$ErrorActionPreference = "Stop"
$sopTemp = $null

function Find-SopPython {
    $candidates = @()
    if ($env:VIDEO_SOP_PYTHON) { $candidates += $env:VIDEO_SOP_PYTHON }
    $candidates += @("python", "python3")
    foreach ($base in @($env:LOCALAPPDATA, $env:ProgramFiles)) {
        if ($base) {
            $candidates += @(Get-ChildItem -Path (Join-Path $base "Programs/Python/Python*/python.exe") -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName)
            $candidates += @(Get-ChildItem -Path (Join-Path $base "Python*/python.exe") -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName)
        }
    }
    foreach ($candidate in $candidates) {
        $command = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($command -and $command.Source -notlike '*\WindowsApps\python*.exe') {
            & $command.Source -c "import sys; raise SystemExit(sys.version_info < (3, 11))" 2>$null
            if ($LASTEXITCODE -eq 0) { return $command.Source }
        }
    }
    return $null
}

try {
    $sopPython = Find-SopPython
    if (-not $sopPython) {
        if ($SkipSystemDeps -or $DryRun) { throw "请先配置 Python 3.11+；当前选项不修改系统。" }
        if (-not (Get-Command winget -ErrorAction SilentlyContinue)) { throw "需要 Windows App Installer（winget）或现有 Python 3.11+。" }
        & winget install --id Python.Python.3.13 --exact --source winget --scope user --silent --accept-package-agreements --accept-source-agreements --disable-interactivity
        if ($LASTEXITCODE -ne 0) { throw "Python 安装失败，请检查 winget。" }
        $env:PATH = [Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [Environment]::GetEnvironmentVariable("PATH", "User")
        $sopPython = Find-SopPython
        if (-not $sopPython) { throw "安装后未找到 Python，请重新打开终端后重试。" }
    }
    $sopSource = $null
    if ($PSScriptRoot -and (Test-Path (Join-Path $PSScriptRoot "SKILL.md"))) { $sopSource = $PSScriptRoot }
    if (-not $sopSource) {
        $sopRef = if ($env:VIDEO_SOP_REF) { $env:VIDEO_SOP_REF } else { "main" }
        if ($sopRef -notmatch '^[A-Za-z0-9._-]+$') { throw "版本必须是分支、标签或提交 SHA。" }
        $sopTemp = Join-Path ([IO.Path]::GetTempPath()) ([guid]::NewGuid().ToString())
        New-Item -ItemType Directory -Path $sopTemp | Out-Null
        $archive = Join-Path $sopTemp "package.zip"
        Invoke-WebRequest -Uri "https://codeload.github.com/shao60533/industry-chain-3d-video-sop/zip/$sopRef" -OutFile $archive -TimeoutSec 180
        $extract = @'
from pathlib import Path
import sys, zipfile
base = Path(sys.argv[2]).resolve()
with zipfile.ZipFile(sys.argv[1]) as bundle:
    if sum(i.file_size for i in bundle.infolist()) > 128 * 1024 * 1024:
        raise SystemExit("Skill archive exceeds size limit")
    for item in bundle.infolist():
        target = (base / item.filename).resolve()
        if not target.is_relative_to(base) or (item.external_attr >> 16) & 0o170000 == 0o120000:
            raise SystemExit("Unsafe archive path")
    bundle.extractall(base)
'@
        & $sopPython -c $extract $archive (Join-Path $sopTemp "source")
        if ($LASTEXITCODE -ne 0) { throw "技能包解压失败。" }
        $roots = @(Get-ChildItem (Join-Path $sopTemp "source") -Directory | Where-Object { Test-Path (Join-Path $_.FullName "SKILL.md") })
        if ($roots.Count -ne 1) { throw "技能包目录不唯一或不完整。" }
        $sopSource = $roots[0].FullName
    }
    $sopArgs = @((Join-Path $sopSource "scripts/setup.py"))
    if ($Dest) { $sopArgs += @("--dest", $Dest) }
    if ($SkipSystemDeps) { $sopArgs += "--skip-system-deps" }
    if ($NoSmoke) { $sopArgs += "--no-smoke" }
    if ($DryRun) { $sopArgs += "--dry-run" }
    & $sopPython @sopArgs
    if ($LASTEXITCODE -ne 0) { throw "安装或自检未通过。" }
} finally {
    if ($sopTemp -and (Test-Path $sopTemp)) { Remove-Item $sopTemp -Recurse -Force }
}
