@echo off
setlocal
cd /d "%~dp0"

echo Khosla Desktop App Diagnostics
echo ==============================
echo Folder: %CD%
echo.

echo Checking required files...
if exist src\khosla_desktop_app.py (echo OK src\khosla_desktop_app.py) else echo MISSING src\khosla_desktop_app.py
if exist src\khosla_desktop_app.pyw (echo OK src\khosla_desktop_app.pyw) else echo MISSING src\khosla_desktop_app.pyw
if exist run_khosla_desktop.bat (echo OK run_khosla_desktop.bat) else echo MISSING run_khosla_desktop.bat
echo.

echo Checking launcher readiness...
call "%~dp0run_khosla_desktop.bat" --check
set "CHECK_RC=%ERRORLEVEL%"
echo.

echo Checking Python command locations...
where py
where python
where python3
echo.

echo Checking winget availability...
where winget
if %ERRORLEVEL%==0 (
  echo winget is available. The launcher can try automatic Python installation.
) else (
  echo winget is not available. Python must be installed manually from python.org.
)
echo.

echo Checking common Python install folders...
dir "%LOCALAPPDATA%\Programs\Python" /b 2>nul
dir "C:\Program Files\Python*" /b 2>nul
dir "C:\Program Files (x86)\Python*" /b 2>nul
echo.

if "%CHECK_RC%"=="0" (
  echo RESULT: Ready to run.
) else (
  echo RESULT: Requirements are missing. Run run_khosla_desktop.bat to install or open Python download instructions.
)

echo.
pause
