import math
import pytest
from finpay.backend.app.services.cashback_service import (
    calculate_cashback,
    get_tier_rate_multiplier,
    get_tier_cap_multiplier,
    get_tier_monthly_cap_paise,
    BASIC_CATEGORY_RULES
)

def test_rahul_scenario_example():
    """
    Scenario from FinPay specification (Page 1):
    Student Rahul has a BASIC wallet and buys food worth ₹100 at the college canteen.
    • Payment amount: ₹100 = 10,000 paise.
    • Canteen cashback rate for BASIC: 2%.
    • Cashback calculation: ₹100 × 2% = ₹2.
    • Raw cashback: 200 paise.
    """
    amount_paise = 10000  # ₹100
    category = "Canteen"
    tier = "BASIC"
    
    raw_cashback, effective_rate = calculate_cashback(amount_paise, category, tier)
    
    assert raw_cashback == 200  # 200 paise = ₹2.00
    assert effective_rate == 2.0

def test_floor_operation_rule():
    """
    Rule from FinPay specification (Page 2, Section 4):
    'The system calculates cashback in paise and uses the floor operation
    rather than rounding. For example, a calculated cashback of 6.66 paise becomes 6 paise, not 7 paise.'
    """
    # ₹3.33 at Canteen (2.0% for BASIC) -> 333 paise * 0.02 = 6.66 paise -> should be 6 paise
    amount_paise = 333
    raw_cashback, effective_rate = calculate_cashback(amount_paise, "Canteen", "BASIC")
    assert raw_cashback == 6

def test_wallet_tiers_multipliers():
    """
    Tier multipliers from Section 3:
    BASIC:   1.0x rate, 1.0x cap
    PRIME:   1.5x rate, 1.5x cap
    PREMIUM: 2.0x rate, 2.0x cap
    """
    amount_paise = 10000  # ₹100

    # BASIC Canteen: 2.0% -> 200 paise
    cb_basic, rate_basic = calculate_cashback(amount_paise, "Canteen", "BASIC")
    assert cb_basic == 200
    assert rate_basic == 2.0

    # PRIME Canteen: 2.0% * 1.5 = 3.0% -> 300 paise
    cb_prime, rate_prime = calculate_cashback(amount_paise, "Canteen", "PRIME")
    assert cb_prime == 300
    assert rate_prime == 3.0

    # PREMIUM Canteen: 2.0% * 2.0 = 4.0% -> 400 paise
    cb_prem, rate_prem = calculate_cashback(amount_paise, "Canteen", "PREMIUM")
    assert cb_prem == 400
    assert rate_prem == 4.0

def test_all_merchant_categories_basic():
    """
    Rules from Section 4:
    Canteen: 2.0%, cap ₹50 (5000 paise)
    Stationery: 1.0%, cap ₹20 (2000 paise)
    Transport: 3.0%, cap ₹100 (10000 paise)
    Hostel: 0.5%, cap ₹200 (20000 paise)
    Online: 1.0%, cap ₹30 (3000 paise)
    Top-up: 0%, cap 0 paise
    """
    amount_paise = 10000  # ₹100

    # Canteen: 2%
    cb, rate = calculate_cashback(amount_paise, "Canteen", "BASIC")
    assert cb == 200
    assert rate == 2.0
    assert get_tier_monthly_cap_paise("Canteen", "BASIC") == 5000

    # Stationery: 1%
    cb, rate = calculate_cashback(amount_paise, "Stationery", "BASIC")
    assert cb == 100
    assert rate == 1.0
    assert get_tier_monthly_cap_paise("Stationery", "BASIC") == 2000

    # Transport: 3%
    cb, rate = calculate_cashback(amount_paise, "Transport", "BASIC")
    assert cb == 300
    assert rate == 3.0
    assert get_tier_monthly_cap_paise("Transport", "BASIC") == 10000

    # Hostel: 0.5%
    cb, rate = calculate_cashback(amount_paise, "Hostel", "BASIC")
    assert cb == 50
    assert rate == 0.5
    assert get_tier_monthly_cap_paise("Hostel", "BASIC") == 20000

    # Online: 1%
    cb, rate = calculate_cashback(amount_paise, "Online", "BASIC")
    assert cb == 100
    assert rate == 1.0
    assert get_tier_monthly_cap_paise("Online", "BASIC") == 3000

    # Top-up: 0%
    cb, rate = calculate_cashback(amount_paise, "Top-up", "BASIC")
    assert cb == 0
    assert rate == 0.0
    assert get_tier_monthly_cap_paise("Top-up", "BASIC") == 0

def test_monthly_cap_multiplier():
    """Test cap multipliers for PRIME (1.5x) and PREMIUM (2.0x)"""
    # Canteen base cap: 5000 paise
    assert get_tier_monthly_cap_paise("Canteen", "BASIC") == 5000
    assert get_tier_monthly_cap_paise("Canteen", "PRIME") == 7500   # 5000 * 1.5
    assert get_tier_monthly_cap_paise("Canteen", "PREMIUM") == 10000 # 5000 * 2.0

def test_zero_and_negative_amounts():
    cb, rate = calculate_cashback(0, "Canteen", "BASIC")
    assert cb == 0
    cb, rate = calculate_cashback(-500, "Canteen", "BASIC")
    assert cb == 0
