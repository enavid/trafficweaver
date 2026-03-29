@echo off
:: TrafficWeaver – Windows bootstrap + daily runner
:: Place this file anywhere and create a Scheduled Task pointing to it.
:: It installs dependencies on first run, then starts the program.

setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo [TrafficWeaver] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

:: Create virtual environment if it doesn't exist
if not exist ".venv\" (
    echo [TrafficWeaver] Creating virtual environment...
    python -m venv .venv
)

:: Activate venv
call .venv\Scripts\activate.bat

:: Install / upgrade dependencies
echo [TrafficWeaver] Installing dependencies...
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

:: Copy .env from example if not present
if not exist ".env" (
    echo [TrafficWeaver] .env not found. Copying from .env.example...
    copy .env.example .env
    echo [TrafficWeaver] Please edit .env before continuing.
    notepad .env
)

echo [TrafficWeaver] Starting...
:loop
python main.py
echo [TrafficWeaver] Day finished. Sleeping 60 s before next cycle...
timeout /t 60 /nobreak >nul
goto loop
