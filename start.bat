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
echo  ==========================================
echo   StrokeAI v4 - Starting on port 9000
echo  ==========================================
echo.

:: Checks
if not exist "%ROOT%\backend\venv\Scripts\activate.bat" (
    echo  [ERROR] Run setup.bat first!
    pause >nul & exit /b 1
)
if not exist "%ROOT%\frontend\index.html" (
    echo  [ERROR] frontend\index.html missing!
    pause >nul & exit /b 1
)
if exist "%ROOT%\backend\xception_stroke_model.tflite" (
    echo  [OK] Model found - real predictions enabled
) else (
    echo  [WARNING] Model not found - demo mode
    echo  Copy xception_stroke_model.tflite to backend folder
)
echo.

:: Kill anything on port 9000
echo  Clearing port 9000...
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":9000 "') do (
    taskkill /PID %%a /F >nul 2>&1
)
timeout /t 2 /nobreak >nul
echo  [OK] Port 9000 free
echo.

:: Start server
echo  Starting server on port 9000...
start "StrokeAI-v4" cmd /k "title StrokeAI v4 [PORT 9000] && cd /d "%ROOT%\backend" && call venv\Scripts\activate.bat && echo. && echo  ====================================== && echo   StrokeAI v4 running! && echo   Open: http://localhost:9000 && echo   API:  http://localhost:9000/health && echo  ====================================== && echo. && uvicorn main:app --host 0.0.0.0 --port 9000 --reload"

:: Wait for server
echo  Waiting for server...
set /a T=0
:wait
timeout /t 2 /nobreak >nul
curl -s http://localhost:9000/health >nul 2>&1
if not errorlevel 1 goto :ok
set /a T+=1
if !T! lss 15 goto :wait
echo  Server still starting, opening browser anyway...
goto :open

:ok
echo  [OK] Server is ready!

:open
echo.
echo  Opening http://localhost:9000 ...
start "" "http://localhost:9000"

echo.
echo  ==========================================
echo   APP RUNNING at http://localhost:9000
echo  ==========================================
echo.
echo  If you see an error, check the StrokeAI v4 window.
echo  Press any key to close this launcher...
pause >nul
