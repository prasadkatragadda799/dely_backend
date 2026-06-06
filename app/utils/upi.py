"""Helpers to build UPI deep-links and amount-embedded QR codes.

A UPI QR is just the standard ``upi://pay?...`` intent string rendered as a QR;
any UPI app (GPay/PhonePe/Paytm) reads it and pre-fills the amount. No payment
gateway or API key is required — only a merchant UPI ID (VPA).
"""
from __future__ import annotations

import base64
import io
from urllib.parse import quote


def build_upi_uri(
    vpa: str,
    payee_name: str,
    amount: float,
    note: str = "",
    ref: str = "",
) -> str:
    """Build a UPI intent URI with the amount pre-filled."""
    parts = [
        f"pa={quote(vpa)}",
        f"pn={quote(payee_name or 'Merchant')}",
        f"am={amount:.2f}",
        "cu=INR",
    ]
    if note:
        parts.append(f"tn={quote(note)}")
    if ref:
        parts.append(f"tr={quote(ref)}")
    return "upi://pay?" + "&".join(parts)


def qr_png_data_uri(text: str) -> str:
    """Return a base64 PNG data URI of a QR encoding ``text`` (Pillow-backed)."""
    import qrcode

    img = qrcode.make(text)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def upi_qr_payload(
    vpa: str,
    payee_name: str,
    amount: float,
    order_number: str | None,
    order_id: str,
) -> dict:
    """Full payload the apps need to render the QR + a 'Pay with UPI app' button."""
    note = f"Order {order_number}".strip() if order_number else "Order payment"
    ref = (order_number or order_id or "").replace(" ", "")
    uri = build_upi_uri(vpa, payee_name, float(amount), note, ref)
    return {
        "upiUri": uri,
        "qrImage": qr_png_data_uri(uri),
        "amount": round(float(amount), 2),
        "vpa": vpa,
        "payeeName": payee_name,
    }
