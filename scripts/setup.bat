@echo off
REM Bootstrap Harmonix: create venv (Python 3.12) and install dependencies.
where uv >nul 2>nul
if %errorlevel% neq 0 (
    echo Installing uv...
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    set "PATH=%USERPROFILE%\.local\bin;%PATH%"
)
uv venv --python 3.12
uv sync
echo.
echo Setup complete. Run "uv run python -m harmonix.main --text" to test.
