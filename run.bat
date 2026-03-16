@echo off
echo Starting SATYA Platform...

echo Starting Backend...
start cmd /k "cd backend && call venv\Scripts\activate && python app.py"

echo Starting Frontend...
start cmd /k "cd frontend && npm run dev"

echo.
echo SATYA is starting up in separate windows.
echo Frontend should be available at http://localhost:5173
echo Backend should be available at http://localhost:5000
echo.
pause
