@echo off
setlocal EnableDelayedExpansion

if not defined STROKEAI_RUNNING (
    set STROKEAI_RUNNING=1
    cmd /k ""%~f0""
    exit /b
)

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

cls
echo.
echo  ============================================
echo   StrokeAI v4 - Setup
echo   PORT: 9000
echo  ============================================
echo.
echo  Press any key to begin...
pause >nul

:: Find Python 3.11
echo.
echo  [1/3] Finding Python 3.11...
set "PY311="
if exist "C:\Python311\python.exe"                                          set "PY311=C:\Python311\python.exe"
if exist "C:\Program Files\Python311\python.exe"                            set "PY311=C:\Program Files\Python311\python.exe"
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"              set "PY311=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
if exist "%USERPROFILE%\AppData\Local\Programs\Python\Python311\python.exe" set "PY311=%USERPROFILE%\AppData\Local\Programs\Python\Python311\python.exe"

if not defined PY311 (
    py -3.11 --version >nul 2>&1
    if not errorlevel 1 (
        for /f "usebackq tokens=*" %%i in (`py -3.11 -c "import sys; print(sys.executable)"`) do set "PY311=%%i"
    )
)

if not defined PY311 (
    echo  [ERROR] Python 3.11 not found.
    echo  Get it from: https://www.python.org/downloads/releases/python-3119/
    echo  CHECK "Add Python to PATH"
    start "" "https://www.python.org/downloads/releases/python-3119/"
    pause >nul & exit /b 1
)
echo  [OK] !PY311!
"!PY311!" --version
echo.
echo  Press any key to continue...
pause >nul

:: Setup backend
echo.
echo  [2/3] Setting up backend...
if exist "%ROOT%\backend\venv" (
    echo  Removing old venv...
    rmdir /s /q "%ROOT%\backend\venv"
)
cd /d "%ROOT%\backend"
"!PY311!" -m venv venv
call venv\Scripts\activate.bat
echo  Python in venv:
python --version
echo.
echo  Installing packages (TensorFlow ~500MB, be patient)...
python -m pip install --upgrade pip -q
pip install setuptools==69.5.1 wheel==0.43.0 -q
pip install Pillow==10.2.0 --only-binary=:all: -q
pip install numpy==1.26.4 -q
echo  Installing TensorFlow...
pip install tensorflow==2.16.1
if errorlevel 1 ( pip install tensorflow-cpu==2.16.1 )
pip install fastapi==0.111.0 -q
pip install uvicorn[standard]==0.30.1 -q
pip install python-multipart==0.0.9 -q
pip install anthropic==0.28.0 -q
pip install python-dotenv==1.0.1 -q
echo  [OK] All packages installed
echo.
echo  Press any key to continue...
pause >nul

:: Check frontend
echo.
echo  [3/3] Checking frontend...
if exist "%ROOT%\frontend\index.html" (
    echo  [OK] frontend\index.html found
) else (
    echo  [ERROR] frontend\index.html MISSING
    pause >nul & exit /b 1
)

echo.
echo  ============================================
echo   SETUP COMPLETE
echo  ============================================
echo.
echo  Double-click start.bat to launch.
echo  App will open at: http://localhost:9000
echo.
echo  Press any key to close...
pause >nul
