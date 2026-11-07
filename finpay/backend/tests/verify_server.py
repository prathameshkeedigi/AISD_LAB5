import sys, os
sys.path.insert(0, os.getcwd())

from starlette.testclient import TestClient
from finpay.backend.app.main import app

def verify():
    client = TestClient(app, raise_server_exceptions=False)
    # Health check
    r = client.get("/api/health")
    print("HEALTH STATUS:", r.status_code, r.json())
    assert r.status_code == 200

    # Frontend root
    r_front = client.get("/")
    print("FRONTEND ROOT STATUS:", r_front.status_code, "HTML Length:", len(r_front.text))
    assert r_front.status_code == 200
    assert "FinPay" in r_front.text

    # Merchants API
    r_merchants = client.get("/api/merchants")
    print("MERCHANTS STATUS:", r_merchants.status_code, "Count:", len(r_merchants.json()))
    assert r_merchants.status_code == 200

    # Rules API
    r_rules = client.get("/api/reconciliation/rules")
    print("RULES STATUS:", r_rules.status_code, "Count:", len(r_rules.json()))
    assert r_rules.status_code == 200

    # Login Rahul
    r_login = client.post("/api/auth/login", json={"email": "rahul@campus.edu", "password": "password123"})
    print("LOGIN STATUS:", r_login.status_code)
    assert r_login.status_code == 200
    token = r_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Wallet
    r_wallet = client.get("/api/wallet/me", headers=headers)
    print("WALLET STATUS:", r_wallet.status_code, r_wallet.json()["user_name"], "Tier:", r_wallet.json()["tier"])
    assert r_wallet.status_code == 200

    # Payment preview
    canteen_id = r_merchants.json()[0]["id"]
    r_prev = client.post(
        "/api/payments/preview",
        headers=headers,
        json={"merchant_id": canteen_id, "amount_rupees": 100.0}
    )
    print("PREVIEW STATUS:", r_prev.status_code, r_prev.json()["raw_cashback_paise"], "paise cashback")
    assert r_prev.status_code == 200
    assert r_prev.json()["raw_cashback_paise"] == 200

    # Pay
    r_pay = client.post(
        "/api/payments/pay",
        headers=headers,
        json={
            "merchant_id": canteen_id,
            "amount_rupees": 100.0,
            "idempotency_key": "verify_server_key_001"
        }
    )
    print("PAY STATUS:", r_pay.status_code, "Cashback awarded:", r_pay.json()["cashback_awarded_paise"], "paise")
    assert r_pay.status_code == 200

    # Pay again with SAME idempotency key (Idempotent replay)
    r_replay = client.post(
        "/api/payments/pay",
        headers=headers,
        json={
            "merchant_id": canteen_id,
            "amount_rupees": 100.0,
            "idempotency_key": "verify_server_key_001"
        }
    )
    print("REPLAY STATUS:", r_replay.status_code, "Is replay:", r_replay.json()["is_idempotent_replay"])
    assert r_replay.status_code == 200
    assert r_replay.json()["is_idempotent_replay"] is True

    print("ALL END-TO-END VERIFICATION CHECKS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    verify()
