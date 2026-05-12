import requests
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

_VARUN_GST_URL = "https://vmsuatkapil.varungroup.com/gst/gstverification"


def verify_gst_number(gst_number: str) -> Optional[Dict[str, Any]]:
    """
    Verify GSTIN via the Varun Group GST verification API.
    Returns a normalized dict on success, None on failure.
    """
    if not gst_number or len(gst_number) != 15:
        return None

    try:
        response = requests.get(
            _VARUN_GST_URL,
            params={"GstIn": gst_number},
            timeout=15,
            verify=False,  # internal UAT server uses a private CA
        )
        response.raise_for_status()
        payload = response.json()

        if payload.get("Status") != 1 or not payload.get("Data"):
            logger.warning("[GST] API returned non-success for %s: %s", gst_number, payload)
            return None

        d = payload["Data"]

        addr_parts = [d.get("AddrBnm", ""), d.get("AddrBno", ""), d.get("AddrFlno", ""), d.get("AddrSt", ""), d.get("AddrLoc", "")]
        address_line = ", ".join(p for p in addr_parts if p)

        return {
            "gst_number": d.get("Gstin", gst_number),
            "legal_name": d.get("LegalName", ""),
            "trade_name": d.get("TradeName", ""),
            "status": d.get("Status", ""),
            "registration_date": d.get("DtReg", ""),
            "business_type": d.get("TxpType", ""),
            "pan_number": d.get("panNumber", ""),
            "address": {
                "street": address_line,
                "city": d.get("AddrLoc", ""),
                "state": str(d.get("StateCode", "")),
                "pincode": str(d.get("AddrPncd", "")),
            },
        }

    except requests.RequestException:
        logger.exception("[GST] Request to Varun GST API failed for %s", gst_number)
        return None
    except Exception:
        logger.exception("[GST] Unexpected error verifying %s", gst_number)
        return None
