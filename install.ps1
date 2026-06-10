param(
    [switch]$WithPaddleOCR,
    [switch]$NoPaddleOCR
)

$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$AppDir = Join-Path $HOME ".image-context-bridge"
$BinDir = Join-Path $HOME ".local\bin"
$VenvDir = Join-Path $AppDir ".venv"

$InstallPaddle = $false
if ($WithPaddleOCR) { $InstallPaddle = $true }
if ($NoPaddleOCR) { $InstallPaddle = $false }

Write-Host "Installing Image Context Bridge..."
Write-Host "OS: Windows"
Write-Host "Install PaddleOCR: $InstallPaddle"

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

$AgentSkillDir = Join-Path $HOME ".agents\skills\image-context"
$ClaudeSkillDir = Join-Path $HOME ".claude\skills\image-context"
$CodexSkillDir = Join-Path $HOME ".codex\skills\image-context"
New-Item -ItemType Directory -Force -Path $AgentSkillDir, $ClaudeSkillDir, $CodexSkillDir | Out-Null
Copy-Item -Force -Recurse (Join-Path $RootDir "skills\image-context\*") $AgentSkillDir
Copy-Item -Force -Recurse (Join-Path $RootDir "skills\image-context\*") $ClaudeSkillDir
Copy-Item -Force -Recurse (Join-Path $RootDir "skills\image-context\*") $CodexSkillDir

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
