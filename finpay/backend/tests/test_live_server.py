import sys, os, time, threading
import urllib.request, json
import uvicorn

sys.path.insert(0, os.getcwd())
from finpay.backend.app.main import app

def run_uvicorn():
    config = uvicorn.Config(app, host="127.0.0.1", port=8877, log_level="warning")
    server = uvicorn.Server(config)
    server.run()

def test_live():
    thread = threading.Thread(target=run_uvicorn, daemon=True)
    thread.start()
    time.sleep(2)  # Give server time to start

    base_url = "http://127.0.0.1:8877"

    # 1. Health
    with urllib.request.urlopen(f"{base_url}/api/health") as resp:
        data = json.loads(resp.read().decode())
        print("HEALTH CHECK:", resp.status, data)
        assert resp.status == 200

    # 2. Frontend Root
    with urllib.request.urlopen(f"{base_url}/") as resp:
        html = resp.read().decode()
        print("FRONTEND ROOT:", resp.status, "HTML Length:", len(html))
        assert resp.status == 200
        assert "FinPay" in html

    # 3. Static CSS & JS
    with urllib.request.urlopen(f"{base_url}/static/app.js") as resp:
        js = resp.read().decode()
        print("STATIC JS:", resp.status, "Length:", len(js))
        assert resp.status == 200

    # 4. Merchants
    with urllib.request.urlopen(f"{base_url}/api/merchants") as resp:
        merchants = json.loads(resp.read().decode())
        print("MERCHANTS COUNT:", len(merchants))
        assert len(merchants) >= 5

    # 5. Login Rahul
    req = urllib.request.Request(
        f"{base_url}/api/auth/login",
        data=json.dumps({"email": "rahul@campus.edu", "password": "password123"}).encode(),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        auth_data = json.loads(resp.read().decode())
        token = auth_data["access_token"]
        print("LOGIN SUCCESSFUL: Rahul token acquired.")

    # 6. Wallet
    req_wallet = urllib.request.Request(
        f"{base_url}/api/wallet/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(req_wallet) as resp:
        wallet = json.loads(resp.read().decode())
        print("WALLET DATA: Balance =", wallet["balance_rupees"], "Tier =", wallet["tier"])

    # 7. Make Payment (Rahul at Canteen ₹100)
    canteen = [m for m in merchants if m["category"] == "Canteen"][0]
    idemp_key = f"live_test_{int(time.time())}"
    req_pay = urllib.request.Request(
        f"{base_url}/api/payments/pay",
        data=json.dumps({
            "merchant_id": canteen["id"],
            "amount_rupees": 100.0,
            "idempotency_key": idemp_key
        }).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(req_pay) as resp:
        pay_result = json.loads(resp.read().decode())
        print("PAY RESULT:", pay_result["status"], "Cashback:", pay_result["cashback_awarded_rupees"], "Replay:", pay_result["is_idempotent_replay"])
        assert pay_result["cashback_awarded_paise"] == 200
        assert pay_result["is_idempotent_replay"] is False

    # 8. Replay payment with same idempotency key
    req_replay = urllib.request.Request(
        f"{base_url}/api/payments/pay",
        data=json.dumps({
            "merchant_id": canteen["id"],
            "amount_rupees": 100.0,
            "idempotency_key": idemp_key
        }).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(req_replay) as resp:
        replay_result = json.loads(resp.read().decode())
        print("IDEMPOTENT REPLAY VERIFIED:", replay_result["is_idempotent_replay"])
        assert replay_result["is_idempotent_replay"] is True

    print("\n>>> ALL LIVE SERVER TESTS PASSED 100% PERFECTLY! <<<")

if __name__ == "__main__":
    test_live()
