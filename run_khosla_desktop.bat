@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "APP_FILE=%~dp0src\khosla_desktop_app.py"
set "LOG_FILE=%~dp0khosla_error.log"
set "CHECK_ONLY="
if /I "%~1"=="--check" set "CHECK_ONLY=1"
if exist "%LOG_FILE%" del "%LOG_FILE%" >nul 2>nul

echo Khosla Hydraulic Foundation Designer
echo ===================================
echo.

if not exist "%APP_FILE%" (
  echo ERROR: src\khosla_desktop_app.py was not found in this folder.
  echo Folder: %CD%
  > "%LOG_FILE%" echo ERROR: src\khosla_desktop_app.py was not found in this folder.
  >> "%LOG_FILE%" echo Folder: %CD%
  pause
  exit /b 1
)

call :find_python
if not defined PY_READY (
  if defined CHECK_ONLY (
    echo Python 3.10+ with Tkinter was not found.
    > "%LOG_FILE%" echo Python 3.10+ with Tkinter was not found.
    >> "%LOG_FILE%" echo Install Python 3.10 or newer from https://www.python.org/downloads/windows/
    >> "%LOG_FILE%" echo During installation, tick: Add python.exe to PATH
    exit /b 1
  )
  call :install_python
  call :find_python
)

if not defined PY_READY (
  echo.
  echo ERROR: Python 3.10+ with Tkinter is still not available.
  echo Install Python from https://www.python.org/downloads/windows/
  echo During installation, tick: Add python.exe to PATH
  echo.
  > "%LOG_FILE%" echo ERROR: Python 3.10+ with Tkinter is still not available.
  >> "%LOG_FILE%" echo Install Python from https://www.python.org/downloads/windows/
  >> "%LOG_FILE%" echo During installation, tick: Add python.exe to PATH
  pause
  exit /b 1
)

echo Python ready: %PY_LABEL%
echo.

if defined CHECK_ONLY (
  echo Deployment check passed. The desktop app requirements are available.
  exit /b 0
)

call :run_app
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" (
  echo The app stopped with error code %RC%.
  echo If khosla_error.log exists, open it and send the contents.
  echo.
  pause
)
exit /b %RC%

:find_python
set "PY_READY="
set "PY_MODE="
set "PY_EXE="
set "PY_LABEL="

if exist "%~dp0python\python.exe" (
  call :test_python_exe "%~dp0python\python.exe" "Bundled portable Python"
  if defined PY_READY exit /b 0
)

where py >nul 2>nul
if not errorlevel 1 (
  py -3 -c "import sys, tkinter; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
  if not errorlevel 1 (
    set "PY_READY=1"
    set "PY_MODE=PYLAUNCHER"
    set "PY_LABEL=py -3"
    exit /b 0
  )
)

for /f "delims=" %%P in ('where python 2^>nul') do (
  call :test_python_exe "%%~fP" "Python from PATH"
  if defined PY_READY exit /b 0
)

for /f "delims=" %%P in ('where python3 2^>nul') do (
  call :test_python_exe "%%~fP" "Python3 from PATH"
  if defined PY_READY exit /b 0
)

for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
  call :test_python_exe "%%~fD\python.exe" "Python in LocalAppData"
  if defined PY_READY exit /b 0
)

for /d %%D in ("C:\Program Files\Python3*") do (
  call :test_python_exe "%%~fD\python.exe" "Python in Program Files"
  if defined PY_READY exit /b 0
)

for /d %%D in ("C:\Program Files (x86)\Python3*") do (
  call :test_python_exe "%%~fD\python.exe" "Python in Program Files x86"
  if defined PY_READY exit /b 0
)

exit /b 0

:test_python_exe
set "CANDIDATE=%~1"
if not exist "%CANDIDATE%" exit /b 1
"%CANDIDATE%" -c "import sys, tkinter; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if errorlevel 1 exit /b 1
set "PY_READY=1"
set "PY_MODE=EXE"
set "PY_EXE=%CANDIDATE%"
set "PY_LABEL=%~2: %CANDIDATE%"
exit /b 0

:install_python
echo Python 3.10+ with Tkinter was not found.
echo.
where winget >nul 2>nul
if errorlevel 1 goto manual_python_install

echo Attempting automatic Python 3.12 install using winget...
echo This may ask for Windows permission.
echo.
winget install --id Python.Python.3.12 -e --source winget --accept-package-agreements --accept-source-agreements
if errorlevel 1 goto manual_python_install
echo.
echo Python installation finished. Checking again...
exit /b 0

:manual_python_install
echo.
echo Automatic installation is not available on this computer.
echo Opening the official Python download page.
echo.
echo Install Python 3.10 or newer and tick:
echo   Add python.exe to PATH
echo.
start "" "https://www.python.org/downloads/windows/"
pause
exit /b 0

:run_app
if /I "%PY_MODE%"=="PYLAUNCHER" (
  py -3 -m py_compile "%APP_FILE%" > "%LOG_FILE%" 2>&1
  if errorlevel 1 exit /b %ERRORLEVEL%
  py -3 "%APP_FILE%" >> "%LOG_FILE%" 2>&1
  exit /b %ERRORLEVEL%
)

if /I "%PY_MODE%"=="EXE" (
  "%PY_EXE%" -m py_compile "%APP_FILE%" > "%LOG_FILE%" 2>&1
  if errorlevel 1 exit /b %ERRORLEVEL%
  "%PY_EXE%" "%APP_FILE%" >> "%LOG_FILE%" 2>&1
  exit /b %ERRORLEVEL%
)

echo ERROR: Internal launcher state is invalid.
> "%LOG_FILE%" echo ERROR: Internal launcher state is invalid.
exit /b 1
