"""
Multi-tier product pricing: unit (base), optional set, optional remaining.
Customer-facing amount = tier base selling + product.commission_cost (same as mobile list API).
"""
from decimal import Decimal
from typing import Any, List, Optional

from fastapi import HTTPException, status

ALLOWED_PRICE_TIERS = frozenset({"unit", "set", "remaining"})


def normalize_price_tier(key: Optional[str]) -> str:
    if not key:
        return "unit"
    k = str(key).strip().lower()
    return k if k in ALLOWED_PRICE_TIERS else "unit"


def tier_base_selling(product: Any, tier: str) -> Decimal:
    """Selling price for the tier before commission."""
    t = normalize_price_tier(tier)
    if t == "set" and getattr(product, "set_selling_price", None) is not None:
        return Decimal(str(product.set_selling_price))
    if t == "remaining" and getattr(product, "remaining_selling_price", None) is not None:
        return Decimal(str(product.remaining_selling_price))
    sp = getattr(product, "selling_price", None) or getattr(product, "price", None) or Decimal("0")
    return Decimal(str(sp))


def tier_mrp(product: Any, tier: str) -> Decimal:
    t = normalize_price_tier(tier)
    if t == "set" and getattr(product, "set_selling_price", None) is not None:
        m = getattr(product, "set_mrp", None) or getattr(product, "mrp", None)
        return Decimal(str(m)) if m is not None else Decimal("0")
    if t == "remaining" and getattr(product, "remaining_selling_price", None) is not None:
        m = getattr(product, "remaining_mrp", None) or getattr(product, "mrp", None)
        return Decimal(str(m)) if m is not None else Decimal("0")
    m = getattr(product, "mrp", None) or getattr(product, "original_price", None)
    if m is not None:
        return Decimal(str(m))
    return tier_base_selling(product, "unit")


def customer_price_with_commission(product: Any, tier: str) -> Decimal:
    base = tier_base_selling(product, tier)
    comm = getattr(product, "commission_cost", None) or Decimal("0")
    return base + Decimal(str(comm))


def tier_is_configured(product: Any, tier: str) -> bool:
    t = normalize_price_tier(tier)
    if t == "unit":
        return True
    if t == "set":
        return getattr(product, "set_selling_price", None) is not None
    if t == "remaining":
        return getattr(product, "remaining_selling_price", None) is not None
    return False


def assert_tier_allowed(product: Any, tier: str) -> None:
    t = normalize_price_tier(tier)
    if not tier_is_configured(product, t):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Price option '{t}' is not available for this product",
        )


def discount_percent(mrp: Decimal, selling_with_commission: Decimal) -> float:
    if not mrp or mrp <= 0:
        return 0.0
    return round(float(((mrp - selling_with_commission) / mrp) * 100), 2)


def build_price_options_for_api(product: Any) -> List[dict]:
    """Payload for mobile: list of selectable tiers (unit always; set/remaining if configured)."""
    out: List[dict] = []
    labels = {"unit": "Unit", "set": "Set", "remaining": "Remaining"}
    for tier in ("unit", "set", "remaining"):
        if not tier_is_configured(product, tier):
            continue
        sell = customer_price_with_commission(product, tier)
        mrp = tier_mrp(product, tier)
        out.append(
            {
                "key": tier,
                "label": labels[tier],
                "sellingPrice": float(sell),
                "mrp": float(mrp),
                "discount": discount_percent(mrp, sell),
            }
        )
    return out
