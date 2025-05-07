@echo off
REM Launch script for Connected Vehicle Platform

echo Starting Connected Vehicle Platform...

REM Load environment variables from .env.azure
if exist .env.azure (
    for /f "tokens=*" %%a in (.env.azure) do (
        set %%a
    )
    echo Environment variables loaded from .env.azure
) else (
    echo WARNING: .env.azure file not found
    echo Please run utils\azure_init.py first or create .env.azure manually
)

REM Set logging level
set LOG_LEVEL=INFO

REM Start the FastAPI server
echo Starting FastAPI server...
uvicorn main:app --reload --host 0.0.0.0 --port 8000

echo Server is running at http://localhost:8000
