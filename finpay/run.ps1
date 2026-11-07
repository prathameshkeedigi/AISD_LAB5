Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   Starting FinPay Campus Digital Wallet & Payment App" -ForegroundColor Green
Write-Host "   Access URL: http://127.0.0.1:8000" -ForegroundColor Yellow
Write-Host "   Swagger API Docs: http://127.0.0.1:8000/docs" -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Cyan
python -m uvicorn finpay.backend.app.main:app --host 127.0.0.1 --port 8000 --reload
