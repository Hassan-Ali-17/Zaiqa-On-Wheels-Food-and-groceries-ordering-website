#!/bin/bash
echo "============================================"
echo " QuickBite - Setup and Run"
echo "============================================"
cd backend
pip install flask flask-cors
echo ""
echo "Starting QuickBite backend..."
echo "Open your browser at: http://127.0.0.1:5000"
echo ""
echo "IMPORTANT: Do NOT delete food_delivery.db"
echo "That file contains all your restaurants, users and orders!"
echo ""
python3 app.py
