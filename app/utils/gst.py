import re
import requests
import logging
from fastapi import HTTPException, status
from app.config import settings

logger = logging.getLogger(__name__)

_GST_REGEX = re.compile(r'^\d{2}[A-Z0-9]{10}[1-9A-Z]Z[A-Z0-9]$')
_CASHFREE_URL = "https://api.cashfree.com/verification/gstin"


def validate_gst_format(gst_number: str) -> str:
    """Normalize and format-check a GSTIN. Returns uppercased value or raises 400."""
    gst = gst_number.strip().upper()
    if len(gst) != 15:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GST number must be exactly 15 characters",
        )
    if not _GST_REGEX.match(gst):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid GST number format",
        )
    return gst


def verify_gst_with_cashfree(gst_number: str) -> dict:
    """
    Verify GSTIN via Cashfree VRS API.
    Returns the verified business details dict on success.
    Raises HTTPException on invalid GSTIN or API failure.
    """
    if not settings.CASHFREE_CLIENT_ID or not settings.CASHFREE_CLIENT_SECRET:
        logger.warning("[GST] Cashfree credentials not configured, skipping live verification")
        return {}

    try:
        response = requests.post(
            _CASHFREE_URL,
            json={"gstin": gst_number},
            headers={
                "x-client-id": settings.CASHFREE_CLIENT_ID,
                "x-client-secret": settings.CASHFREE_CLIENT_SECRET,
                "x-api-version": "2022-10-26",
                "Content-Type": "application/json",
            },
            timeout=10,
        )
    except requests.RequestException:
        logger.exception("[GST] Cashfree VRS request failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="GST verification service unavailable. Please try again.",
        )

    if response.status_code == 422 or response.status_code == 400:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or unregistered GST number",
        )

    if response.status_code == 401:
        logger.error("[GST] Cashfree authentication failed — check credentials")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="GST verification service error. Please try again.",
        )

    if not response.ok:
        logger.error("[GST] Cashfree VRS unexpected status %s: %s", response.status_code, response.text)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="GST verification failed. Please try again.",
        )

    data = response.json()

    # Cashfree returns gstin_status: "Active" for valid registrations
    gstin_status = (data.get("gstin_status") or data.get("data", {}).get("gstin_status") or "").strip()
    if gstin_status and gstin_status.lower() != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"GST number is not active (status: {gstin_status})",
        )

    return data


def validate_and_verify_gst(gst_number: str) -> str:
    """Format-check then live-verify a GSTIN. Returns normalized GSTIN."""
    gst = validate_gst_format(gst_number)
    verify_gst_with_cashfree(gst)
    return gst
