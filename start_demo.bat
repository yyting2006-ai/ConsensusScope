@echo off
setlocal

cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    set "PYTHON=py -3"
) else (
    set "PYTHON=python"
)

if not exist ".venv\Scripts\activate.bat" (
    %PYTHON% -m venv .venv
    if errorlevel 1 (
        echo Failed to create Python virtual environment.
        echo Please install Python 3.10 or newer and make sure it is on PATH.
        pause
        exit /b 1
    )
)

call ".venv\Scripts\activate.bat"

python -m pip install -U pip
if errorlevel 1 (
    echo Failed to update pip.
    pause
    exit /b 1
)

python -m pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo Starting ConsensusScope at http://localhost:8502
echo Keep this window open while using the demo.
echo.

streamlit run app\streamlit_app.py --server.port 8502

pause
