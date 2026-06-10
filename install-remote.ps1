param(
    [switch]$WithPaddleOCR,
    [switch]$NoPaddleOCR,
    [string]$Target = $env:TEXTVISION_TARGET,
    [string]$AppDir = $env:TEXTVISION_APP_DIR,
    [string]$BinDir = $env:TEXTVISION_BIN_DIR,
    [string]$SkillDir = $env:TEXTVISION_SKILL_DIR,
    [string]$Ref = $env:TEXTVISION_REF
)

$ErrorActionPreference = "Stop"

$Repo = if ($env:TEXTVISION_REPO) { $env:TEXTVISION_REPO } else { "huaqing0/textvision" }
if ([string]::IsNullOrWhiteSpace($Ref)) {
    $Ref = "main"
}
$Url = if ($env:TEXTVISION_ZIP_URL) {
    $env:TEXTVISION_ZIP_URL
} else {
    "https://codeload.github.com/$Repo/zip/$Ref"
}

$TempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("textvision-" + [System.Guid]::NewGuid().ToString("N"))
$ZipPath = Join-Path $TempDir "source.zip"

try {
    New-Item -ItemType Directory -Force -Path $TempDir | Out-Null
    Write-Host "Downloading TextVision from $Repo@$Ref..."
    Invoke-WebRequest -Uri $Url -OutFile $ZipPath -UseBasicParsing
    Expand-Archive -Path $ZipPath -DestinationPath $TempDir -Force

    $SourceDir = Get-ChildItem -Path $TempDir -Directory |
        Where-Object { Test-Path (Join-Path $_.FullName "install.ps1") } |
        Select-Object -First 1

    if ($null -eq $SourceDir) {
        throw "Downloaded archive did not contain install.ps1."
    }

    $InstallArgs = @()
    if ($WithPaddleOCR -or $env:TEXTVISION_WITH_PADDLEOCR -eq "1") {
        $InstallArgs += "-WithPaddleOCR"
    }
    if ($NoPaddleOCR -or $env:TEXTVISION_NO_PADDLEOCR -eq "1") {
        $InstallArgs += "-NoPaddleOCR"
    }
    if (-not [string]::IsNullOrWhiteSpace($Target)) {
        $InstallArgs += @("-Target", $Target)
    }
    if (-not [string]::IsNullOrWhiteSpace($AppDir)) {
        $InstallArgs += @("-AppDir", $AppDir)
    }
    if (-not [string]::IsNullOrWhiteSpace($BinDir)) {
        $InstallArgs += @("-BinDir", $BinDir)
    }
    if (-not [string]::IsNullOrWhiteSpace($SkillDir)) {
        $InstallArgs += @("-SkillDir", $SkillDir)
    }

    & (Join-Path $SourceDir.FullName "install.ps1") @InstallArgs
} finally {
    if (Test-Path $TempDir) {
        Remove-Item -Recurse -Force $TempDir
    }
}
