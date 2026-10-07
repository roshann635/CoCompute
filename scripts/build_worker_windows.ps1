# CoCompute Windows Worker Packaging Script
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "      Building CoCompute Standalone Worker Executable       " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$RepoRoot = (Get-Item $PSScriptRoot).Parent.FullName
Set-Location $RepoRoot

# Clean previous build artifacts
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
$DistDir = Join-Path $RepoRoot "dist\windows"
if (Test-Path $DistDir) { Remove-Item -Recurse -Force $DistDir }
New-Item -ItemType Directory -Force -Path $DistDir | Out-Null

Write-Host "Running PyInstaller packaging..." -ForegroundColor Yellow
$SpecPath = Join-Path $RepoRoot "packaging\windows\CoComputeWorker.spec"
pyinstaller --clean --distpath $DistDir $SpecPath

$ExePath = Join-Path $DistDir "CoComputeWorker.exe"
if (Test-Path $ExePath) {
    $Size = (Get-Item $ExePath).Length / 1MB
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host "[SUCCESS] Standalone Worker created: $ExePath ($([math]::Round($Size, 2)) MB)" -ForegroundColor Green
    Write-Host "Ready for zero-friction distribution on Windows lab machines." -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Green
} else {
    Write-Error "Build failed: $ExePath not found."
    exit 1
}
