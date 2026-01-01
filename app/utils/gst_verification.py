import requests
from app.config import settings
from typing import Optional, Dict, Any


def verify_gst_number(gst_number: str) -> Optional[Dict[str, Any]]:
    """
    Verify GST number using external API
    Returns GST details if valid, None otherwise
    """
    try:
        # This is a placeholder - replace with actual GST API integration
        # Example API call:
        # response = requests.get(
        #     f"{settings.GST_VERIFICATION_API_URL}/verify",
        #     params={"gst": gst_number},
        #     headers={"Authorization": f"Bearer {settings.GST_API_KEY}"}
        # )
        # if response.status_code == 200:
        #     return response.json()
        
        # For now, return mock data
        if len(gst_number) == 15 and gst_number[:2].isdigit():
            return {
                "gst_number": gst_number,
                "legal_name": "Sample Business Name",
                "trade_name": "Sample Trade Name",
                "status": "Active",
                "registration_date": "2020-01-01",
                "business_type": "Regular",
                "address": {
                    "street": "Sample Street",
                    "city": "Sample City",
                    "state": "Sample State",
                    "pincode": "123456"
                }
            }
        return None
    except Exception as e:
        print(f"Error verifying GST: {e}")
        return None

