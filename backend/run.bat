@echo off
set PYTHONPATH=%~dp0;%PYTHONPATH%
"C:\Users\max\miniconda3\envs\api\python.exe" -m uvicorn app.main:app --reload --port 8000
pause
