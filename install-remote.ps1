param(
    [switch]$WithPaddleOCR,
    [switch]$NoPaddleOCR,
    [string]$Ref = $env:IMAGE_CONTEXT_BRIDGE_REF
)

$ErrorActionPreference = "Stop"

$Repo = if ($env:IMAGE_CONTEXT_BRIDGE_REPO) { $env:IMAGE_CONTEXT_BRIDGE_REPO } else { "huaqing0/image-context-bridge" }
if ([string]::IsNullOrWhiteSpace($Ref)) {
    $Ref = "main"
}
$Url = if ($env:IMAGE_CONTEXT_BRIDGE_ZIP_URL) {
    $env:IMAGE_CONTEXT_BRIDGE_ZIP_URL
} else {
    "https://codeload.github.com/$Repo/zip/$Ref"
}

$TempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("image-context-bridge-" + [System.Guid]::NewGuid().ToString("N"))
$ZipPath = Join-Path $TempDir "source.zip"

try {
    New-Item -ItemType Directory -Force -Path $TempDir | Out-Null
    Write-Host "Downloading Image Context Bridge from $Repo@$Ref..."
    Invoke-WebRequest -Uri $Url -OutFile $ZipPath -UseBasicParsing
    Expand-Archive -Path $ZipPath -DestinationPath $TempDir -Force

    $SourceDir = Get-ChildItem -Path $TempDir -Directory |
        Where-Object { Test-Path (Join-Path $_.FullName "install.ps1") } |
        Select-Object -First 1

    if ($null -eq $SourceDir) {
        throw "Downloaded archive did not contain install.ps1."
    }

    $InstallArgs = @()
    if ($WithPaddleOCR -or $env:IMAGE_CONTEXT_BRIDGE_WITH_PADDLEOCR -eq "1") {
        $InstallArgs += "-WithPaddleOCR"
    }
    if ($NoPaddleOCR -or $env:IMAGE_CONTEXT_BRIDGE_NO_PADDLEOCR -eq "1") {
        $InstallArgs += "-NoPaddleOCR"
    }

    & (Join-Path $SourceDir.FullName "install.ps1") @InstallArgs
} finally {
    if (Test-Path $TempDir) {
        Remove-Item -Recurse -Force $TempDir
    }
}
