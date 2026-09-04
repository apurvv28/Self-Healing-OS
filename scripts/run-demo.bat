@echo off
REM AegisOS — Live Self-Healing OS Demonstration Script (Windows)
REM Run from CMD or PowerShell: scripts\run-demo.bat

setlocal enabledelayedexpansion

echo ==================================================================
echo          AegisOS -- Autonomous Self-Healing OS Live Demo          
echo ==================================================================
echo.

IF EXIST ".venv\Scripts\python.exe" (
    SET "PYTHON=.venv\Scripts\python.exe"
) ELSE (
    python -m venv .venv
    SET "PYTHON=.venv\Scripts\python.exe"
)

%PYTHON% -c "import uvicorn, fastapi, psutil, sklearn" >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Installing missing dependencies from requirements.txt...
    %PYTHON% -m pip install -r requirements.txt
)

echo Using Python Runtime: %PYTHON%
echo.

echo [Step 1/5] Checking System Baseline Telemetry ^& Active Thresholds...
%PYTHON% agent.py status
echo.
%PYTHON% -c "import time; time.sleep(2)"

echo [Step 2/5] Ingesting Synthetic Failure Scenarios ^& Executing Self-Healing Loop...

echo --> Triggering Scenario: service_failure
%PYTHON% agent.py trigger-scenario --type service_failure
echo.
%PYTHON% -c "import time; time.sleep(2)"

echo --> Triggering Scenario: cpu_overload
%PYTHON% agent.py trigger-scenario --type cpu_overload
echo.
%PYTHON% -c "import time; time.sleep(2)"

echo --> Triggering Scenario: memory_exhaustion
%PYTHON% agent.py trigger-scenario --type memory_exhaustion
echo.
%PYTHON% -c "import time; time.sleep(2)"

echo --> Triggering Scenario: disk_exhaustion
%PYTHON% agent.py trigger-scenario --type disk_exhaustion
echo.
%PYTHON% -c "import time; time.sleep(2)"

echo [Step 3/5] Fetching Recent Incidents from SQLite Audit Log Database...
%PYTHON% agent.py incidents --limit 10
echo.
%PYTHON% -c "import time; time.sleep(2)"

echo [Step 4/5] Computing Self-Healing Success Rate ^& Mean-Time-To-Recovery (MTTR)...
%PYTHON% agent.py metrics
echo.
%PYTHON% -c "import time; time.sleep(2)"

echo [Step 5/5] Launching AegisOS Interactive Web Dashboard ^& REST API...
echo Dashboard Web Interface: http://127.0.0.1:8000
echo Press Ctrl+C to terminate the web server when done.
echo.

%PYTHON% agent.py serve --host 127.0.0.1 --port 8000
