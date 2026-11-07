@echo off
echo Running FinPay Comprehensive Test Suite...
python -m pytest finpay/backend/tests -v
pause
