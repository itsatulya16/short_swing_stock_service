@echo off
REM Runs the Nifty 500 screener. Adjust the paths below to match your setup.

cd /d "%~dp0"

REM If using a virtual environment, uncomment and set the correct path:
REM call venv\Scripts\activate.bat

python screener.py

REM Keep window open on error so you can see what happened (remove if running via Task Scheduler)
if errorlevel 1 pause
