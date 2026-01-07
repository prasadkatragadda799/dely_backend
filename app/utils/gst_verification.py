import requests
from app.config import settings
from typing import Optional, Dict, Any


def verify_gst_number(gst_number: str) -> Optional[Dict[str, Any]]:
    """
    Verify GST number using external API
    Returns GST details if valid, None otherwise
    
    Note: Currently returns mock data. In production, integrate with actual GST API.
    """
    try:
        # Validate GST number format
        if not gst_number or len(gst_number) != 15:
            return None
        
        # Extract state code (first 2 digits)
        state_code = gst_number[:2]
        
        # This is a placeholder - replace with actual GST API integration
        # Example API call:
        # response = requests.get(
        #     f"{settings.GST_VERIFICATION_API_URL}/verify",
        #     params={"gst": gst_number},
        #     headers={"Authorization": f"Bearer {settings.GST_API_KEY}"},
        #     timeout=10  # 10 second timeout
        # )
        # if response.status_code == 200:
        #     return response.json()
        
        # For now, return mock data based on GST number
        # Extract PAN from GST (characters 3-12)
        pan = gst_number[2:12]
        
        # State mapping (first 2 digits)
        state_map = {
            "09": "Uttar Pradesh",
            "27": "Maharashtra",
            "10": "Bihar",
            "07": "Delhi",
            "33": "Tamil Nadu",
            "19": "West Bengal"
        }
        state_name = state_map.get(state_code, "Unknown State")
        
        return {
            "gst_number": gst_number,
            "legal_name": f"Business {pan}",
            "trade_name": f"Trade Name {pan}",
            "status": "Active",
            "registration_date": "2020-01-01",
            "business_type": "Regular",
            "address": {
                "street": f"Business Address for {gst_number}",
                "city": "Sample City",
                "state": state_name,
                "pincode": "123456"
            }
        }
    except Exception as e:
        print(f"Error verifying GST: {e}")
        return None

