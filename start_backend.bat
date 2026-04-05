@echo off
echo.
echo ============================================
echo Virtual Refrigeration System - Backend
echo ============================================
echo.
echo Installing dependencies...
pip install -r requirements.txt

echo.
echo Starting Flask backend...
echo Server will run at: http://localhost:5000
echo.
python app.py

pause
