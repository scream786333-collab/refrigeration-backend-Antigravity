# Virtual Refrigeration System - Start Backend
# Run this script to start the Flask backend

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Virtual Refrigeration System - Backend" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Installing/Updating dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

Write-Host ""
Write-Host "Starting Flask backend..." -ForegroundColor Green
Write-Host "Server will run at: http://localhost:5000" -ForegroundColor Green
Write-Host ""
Write-Host "Once running, open your browser and go to:" -ForegroundColor Cyan
Write-Host "http://localhost:5000/" -ForegroundColor Yellow
Write-Host ""

python app.py
