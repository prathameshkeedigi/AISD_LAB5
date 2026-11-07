import math
from typing import Tuple, Dict

# Tier Multipliers from FinPay Specification
TIER_RATE_MULTIPLIERS: Dict[str, float] = {
    "BASIC": 1.0,
    "PRIME": 1.5,
    "PREMIUM": 2.0,
}

TIER_CAP_MULTIPLIERS: Dict[str, float] = {
    "BASIC": 1.0,
    "PRIME": 1.5,
    "PREMIUM": 2.0,
}

# BASIC-tier rules: Rates in basis points (1% = 100 bps) and monthly caps in paise (₹1 = 100 paise)
BASIC_CATEGORY_RULES: Dict[str, Dict[str, int]] = {
    "Canteen": {
        "base_rate_bps": 200,          # 2.0%
        "base_monthly_cap_paise": 5000 # ₹50 = 5000 paise
    },
    "Stationery": {
        "base_rate_bps": 100,          # 1.0%
        "base_monthly_cap_paise": 2000 # ₹20 = 2000 paise
    },
    "Transport": {
        "base_rate_bps": 300,          # 3.0%
        "base_monthly_cap_paise": 10000# ₹100 = 10000 paise
    },
    "Hostel": {
        "base_rate_bps": 50,           # 0.5%
        "base_monthly_cap_paise": 20000# ₹200 = 20000 paise
    },
    "Online": {
        "base_rate_bps": 100,          # 1.0%
        "base_monthly_cap_paise": 3000 # ₹30 = 3000 paise
    },
    "Top-up": {
        "base_rate_bps": 0,            # 0%
        "base_monthly_cap_paise": 0    # No cashback
    }
}

def get_tier_rate_multiplier(tier: str) -> float:
    return TIER_RATE_MULTIPLIERS.get(tier.upper(), 1.0)

def get_tier_cap_multiplier(tier: str) -> float:
    return TIER_CAP_MULTIPLIERS.get(tier.upper(), 1.0)

def get_tier_monthly_cap_paise(category: str, tier: str) -> int:
    """
    Returns the monthly cashback cap in paise for a given category and wallet tier.
    Applies the tier cap multiplier and floors the result to an exact integer.
    """
    rule = BASIC_CATEGORY_RULES.get(category, {"base_monthly_cap_paise": 0})
    base_cap = rule["base_monthly_cap_paise"]
    cap_mult = get_tier_cap_multiplier(tier)
    return math.floor(base_cap * cap_mult)

def calculate_cashback(amount_paise: int, category: str, tier: str) -> Tuple[int, float]:
    """
    Pure service function that calculates raw cashback for one transaction
    WITHOUT database access.
    
    Rules:
    - Calculates cashback in paise
    - Uses floor operation rather than rounding (e.g. 6.66 paise -> 6 paise)
    - Returns (raw_cashback_paise, effective_rate_percent)
    """
    if amount_paise <= 0:
        return 0, 0.0

    rule = BASIC_CATEGORY_RULES.get(category)
    if not rule:
        return 0, 0.0

    base_rate_bps = rule["base_rate_bps"]
    rate_mult = get_tier_rate_multiplier(tier)
    
    # Effective rate percentage (e.g., 2.0% * 1.5 = 3.0%)
    effective_rate_percent = (base_rate_bps / 100.0) * rate_mult
    
    # Calculate raw cashback in paise strictly using floor operation
    # (amount_paise * (base_rate_bps / 10000) * rate_mult)
    calculated_paise = (amount_paise * (base_rate_bps * rate_mult)) / 10000.0
    raw_cashback_paise = math.floor(calculated_paise)
    
    return int(raw_cashback_paise), float(effective_rate_percent)
