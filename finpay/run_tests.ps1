Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   Executing FinPay Specification Test Suite" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan
python -m pytest finpay/backend/tests -v
