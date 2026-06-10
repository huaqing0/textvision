param(
    [switch]$WithPaddleOCR,
    [switch]$NoPaddleOCR,
    [string]$Target = "",
    [string]$AppDir = "",
    [string]$BinDir = "",
    [string]$SkillDir = ""
)

$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path

if ([string]::IsNullOrWhiteSpace($Target)) {
    $Target = if ($env:IMAGE_CONTEXT_BRIDGE_TARGET) { $env:IMAGE_CONTEXT_BRIDGE_TARGET } else { "claude" }
}
if ([string]::IsNullOrWhiteSpace($AppDir)) {
    $AppDir = if ($env:IMAGE_CONTEXT_BRIDGE_APP_DIR) { $env:IMAGE_CONTEXT_BRIDGE_APP_DIR } else { Join-Path $HOME ".image-context-bridge" }
}
if ([string]::IsNullOrWhiteSpace($BinDir)) {
    $BinDir = if ($env:IMAGE_CONTEXT_BRIDGE_BIN_DIR) { $env:IMAGE_CONTEXT_BRIDGE_BIN_DIR } else { Join-Path $HOME ".local\bin" }
}
if ([string]::IsNullOrWhiteSpace($SkillDir) -and $env:IMAGE_CONTEXT_BRIDGE_SKILL_DIR) {
    $SkillDir = $env:IMAGE_CONTEXT_BRIDGE_SKILL_DIR
}
if (-not [string]::IsNullOrWhiteSpace($SkillDir)) {
    $Target = "custom"
}
$AllowedTargets = @("claude", "codex", "agents", "all", "none", "custom")
if ($AllowedTargets -notcontains $Target) {
    throw "Unknown target: $Target. Use claude, codex, agents, all, none, or custom."
}
if ($Target -eq "custom" -and [string]::IsNullOrWhiteSpace($SkillDir)) {
    throw "Custom target requires -SkillDir or IMAGE_CONTEXT_BRIDGE_SKILL_DIR."
}

$VenvDir = Join-Path $AppDir ".venv"

$InstallPaddle = $false
if ($WithPaddleOCR) { $InstallPaddle = $true }
if ($NoPaddleOCR) { $InstallPaddle = $false }

Write-Host "Installing Image Context Bridge..."
Write-Host "OS: Windows"
Write-Host "Install PaddleOCR: $InstallPaddle"
Write-Host "Install target: $Target"
Write-Host "App dir: $AppDir"
Write-Host "Bin dir: $BinDir"
if (-not [string]::IsNullOrWhiteSpace($SkillDir)) {
    Write-Host "Custom skill dir: $SkillDir"
}

New-Item -ItemType Directory -Force -Path $AppDir, $BinDir, (Join-Path $AppDir "scripts"), (Join-Path $AppDir "hooks"), (Join-Path $AppDir "skills\image-context"), (Join-Path $AppDir "testdata") | Out-Null
Copy-Item -Force -Recurse (Join-Path $RootDir "scripts\*") (Join-Path $AppDir "scripts")
Copy-Item -Force (Join-Path $RootDir "hooks\auto_image_fallback.py") (Join-Path $AppDir "hooks\auto_image_fallback.py")
Copy-Item -Force (Join-Path $RootDir "requirements.txt") (Join-Path $AppDir "requirements.txt")
Copy-Item -Force (Join-Path $RootDir "requirements-paddleocr.txt") (Join-Path $AppDir "requirements-paddleocr.txt")
Copy-Item -Force -Recurse (Join-Path $RootDir "skills\image-context\*") (Join-Path $AppDir "skills\image-context")
Copy-Item -Force (Join-Path $RootDir "testdata\sample.svg") (Join-Path $AppDir "testdata\sample.svg")

python -m venv $VenvDir
$Py = Join-Path $VenvDir "Scripts\python.exe"
& $Py -m pip install --upgrade pip
& $Py -m pip install -r (Join-Path $AppDir "requirements.txt")

if ($InstallPaddle) {
    Write-Host "Installing PaddleOCR backend. This may take a while..."
    & $Py -m pip install -r (Join-Path $AppDir "requirements-paddleocr.txt")
}

$Image2ContextCmd = Join-Path $BinDir "image2context.cmd"
@"
@echo off
"$Py" "$AppDir\scripts\image2context.py" %*
"@ | Set-Content -Encoding ASCII $Image2ContextCmd

$FallbackCmd = Join-Path $BinDir "auto-image-fallback.cmd"
@"
@echo off
"$Py" "$AppDir\hooks\auto_image_fallback.py" %*
"@ | Set-Content -Encoding ASCII $FallbackCmd

function Install-SkillRoot([string]$SkillRoot) {
    $Dest = Join-Path $SkillRoot "image-context"
    New-Item -ItemType Directory -Force -Path $Dest | Out-Null
    Copy-Item -Force -Recurse (Join-Path $RootDir "skills\image-context\*") $Dest
    Write-Host "Skill: $Dest"
}

switch ($Target) {
    "claude" { Install-SkillRoot (Join-Path $HOME ".claude\skills") }
    "codex" { Install-SkillRoot (Join-Path $HOME ".codex\skills") }
    "agents" { Install-SkillRoot (Join-Path $HOME ".agents\skills") }
    "all" {
        Install-SkillRoot (Join-Path $HOME ".claude\skills")
        Install-SkillRoot (Join-Path $HOME ".codex\skills")
        Install-SkillRoot (Join-Path $HOME ".agents\skills")
    }
    "custom" { Install-SkillRoot $SkillDir }
    "none" { Write-Host "Skill: skipped (-Target none)" }
}

& $Py -m py_compile (Join-Path $AppDir "scripts\image2context.py") (Join-Path $AppDir "hooks\auto_image_fallback.py")

Write-Host ""
Write-Host "Installed Image Context Bridge."
Write-Host "Command: $Image2ContextCmd"
Write-Host "Hook helper: $FallbackCmd"
Write-Host ""
Write-Host "Backend policy:"
Write-Host "- Windows: Windows native OCR by default"
Write-Host "- PaddleOCR: optional, install with .\install.ps1 -WithPaddleOCR"
Write-Host "- SVG: direct text/XML parsing"
Write-Host ""
Write-Host "Add $BinDir to PATH if needed. Test with:"
Write-Host "  image2context $AppDir\testdata\sample.svg --json"
