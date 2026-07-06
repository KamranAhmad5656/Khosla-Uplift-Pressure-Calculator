@echo off
setlocal
cd /d "%~dp0"
set "NO_PAUSE="
if /I "%~1"=="--no-pause" set "NO_PAUSE=1"

set "DIST_ROOT=%~dp0dist"
set "DIST_APP=%DIST_ROOT%\Khosla Hydraulic Foundation Designer"

echo Creating deployable desktop package...
echo.

if exist "%DIST_APP%" rmdir /s /q "%DIST_APP%"
mkdir "%DIST_APP%" || exit /b 1

copy /y khosla_desktop_app.py "%DIST_APP%\" >nul
copy /y khosla_desktop_app.pyw "%DIST_APP%\" >nul
copy /y run_khosla_desktop.bat "%DIST_APP%\" >nul
copy /y diagnose_desktop.bat "%DIST_APP%\" >nul
copy /y README_DESKTOP.md "%DIST_APP%\" >nul
copy /y requirements.txt "%DIST_APP%\" >nul
copy /y VALIDATION_NOTES.md "%DIST_APP%\" >nul

echo Done.
echo Deployable folder:
echo %DIST_APP%
echo.
echo Copy that folder to another Windows computer and double-click:
echo run_khosla_desktop.bat
echo.
if not defined NO_PAUSE pause
