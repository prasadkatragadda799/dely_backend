"""Packaging variant labels: Set / Pieces / Pack (admin + mobile)."""
from __future__ import annotations

from typing import Any, Dict, Optional

PACKAGING_LABEL_DISPLAY: dict[str, str] = {
    "set": "Set",
    "pieces": "Pieces",
    "pack": "Pack",
    "unit": "Unit",
    "pair": "Pair",
    "dozen": "Dozen",
}

VALID_PACKAGING_LABEL_TYPES = frozenset(PACKAGING_LABEL_DISPLAY.keys())


def normalize_packaging_label_type(raw: Any) -> Optional[str]:
    if raw is None:
        return None
    s = str(raw).strip().lower()
    if not s or s in ("none", "null", ""):
        return None
    return s if s in VALID_PACKAGING_LABEL_TYPES else None


def format_variant_packaging_line(
    packaging_label_type: Optional[str],
    set_pcs_detail: Optional[str],
    weight: Optional[str],
) -> str:
    """
    Human-readable packaging line for list/detail UIs.
    Backward compatible: if type is missing, shows set_pcs / weight only.
    """
    ptype = (packaging_label_type or "").strip().lower()
    label_word = PACKAGING_LABEL_DISPLAY.get(ptype) if ptype else None
    detail = (set_pcs_detail or "").strip()
    w = (weight or "").strip()

    parts: list[str] = []
    if label_word and detail:
        parts.append(f"{label_word}: {detail}")
    elif label_word:
        parts.append(label_word)
    elif detail:
        parts.append(detail)
    if w:
        parts.append(w)
    return " · ".join(parts)


def variant_row_for_public_api(v: Any, variant_mrp: Any, variant_price: Any, variant_discount: float) -> Dict[str, Any]:
    """Single variant object for GET /products-style responses."""
    ptype = getattr(v, "packaging_label_type", None)
    set_pcs = getattr(v, "set_pcs", None)
    weight = getattr(v, "weight", None)
    return {
        "id": v.id,
        "hsnCode": getattr(v, "hsn_code", None),
        "packagingLabelType": ptype,
        "setPieces": set_pcs,
        "packagingLabel": format_variant_packaging_line(ptype, set_pcs, weight),
        "weight": weight,
        "mrp": float(variant_mrp) if variant_mrp is not None else None,
        "specialPrice": float(variant_price) if variant_price is not None else None,
        "discountPercentage": variant_discount,
        "freeItem": getattr(v, "free_item", None),
    }
