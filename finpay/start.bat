@echo off
echo Starting FinPay Campus Digital Wallet Server...
python -m uvicorn finpay.backend.app.main:app --host 127.0.0.1 --port 8000 --reload
pause
