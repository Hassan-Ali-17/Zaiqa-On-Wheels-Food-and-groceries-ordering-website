@echo off
echo ============================================
echo  QuickBite - Setup and Run
echo ============================================

cd backend

REM Install dependencies
echo Installing Python dependencies...
pip install flask flask-cors

REM Start the server
echo.
echo Starting QuickBite backend...
echo Open your browser at: http://127.0.0.1:5000
echo.
echo IMPORTANT: Do NOT delete food_delivery.db
echo That file contains all your restaurants, users and orders!
echo.
python app.py
pause
