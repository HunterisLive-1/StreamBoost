@echo off
echo ==========================================
echo   StreamBoost V2 - EXE Builder
echo ==========================================
echo.

:: Check PyInstaller
pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] PyInstaller nahi mila, install kar raha hu...
    pip install pyinstaller
)

:: Check dependencies
pip show psutil >nul 2>&1
if %errorlevel% neq 0 pip install psutil

pip show pystray >nul 2>&1
if %errorlevel% neq 0 pip install pystray

pip show Pillow >nul 2>&1
if %errorlevel% neq 0 pip install Pillow

echo.
echo [*] Building StreamBoost.exe ...
echo.

pyinstaller ^
    --onefile ^
    --windowed ^
    --name "StreamBoost" ^
    --hidden-import=psutil ^
    --hidden-import=pystray ^
    --hidden-import=PIL ^
    --hidden-import=tkinter ^
    --uac-admin ^
    streamboost.py

echo.
if exist "dist\StreamBoost.exe" (
    echo [SUCCESS] StreamBoost.exe ready hai!
    echo [PATH] dist\StreamBoost.exe
    echo.
    echo Ab dist folder se StreamBoost.exe share karo!
) else (
    echo [ERROR] Build fail ho gayi. Upar error dekho.
)

echo.
