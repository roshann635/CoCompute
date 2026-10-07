@echo off
echo ============================================================
echo      Building CoCompute Standalone Worker Executable
echo ============================================================

set SCRIPT_DIR=%~dp0
set REPO_ROOT=%SCRIPT_DIR%..
cd /d "%REPO_ROOT%"

echo Cleaning previous builds...
rmdir /s /q build 2>nul
rmdir /s /q dist\windows 2>nul
mkdir dist\windows 2>nul

echo Running PyInstaller...
pyinstaller --clean --distpath dist\windows packaging\windows\CoComputeWorker.spec

if exist dist\windows\CoComputeWorker.exe (
    echo.
    echo ============================================================
    echo [SUCCESS] Built dist\windows\CoComputeWorker.exe
    echo ============================================================
) else (
    echo.
    echo [ERROR] Build failed! Check pyinstaller output.
    exit /b 1
)
