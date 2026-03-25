"""
Maps/Routes endpoints for the mobile app.

At the moment we only expose Google Directions in a way that keeps the API key server-side.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Any, Dict, List, Optional

import re
import requests

from app.config import settings
from app.schemas.common import ResponseModel

router = APIRouter()


def _strip_html(html: Optional[str]) -> str:
    if not html:
        return ""
    # Google returns HTML in `html_instructions`.
    return re.sub(r"<[^>]*>", "", html).strip()


def _decode_polyline(polyline_str: str) -> List[Dict[str, float]]:
    """
    Decode Google Encoded Polyline.

    Returns a list of { latitude, longitude } points.
    """

    index = 0
    lat = 0
    lng = 0
    coordinates: List[Dict[str, float]] = []

    while index < len(polyline_str):
        shift = 0
        result = 0
        while True:
            if index >= len(polyline_str):
                break
            b = ord(polyline_str[index]) - 63
            index += 1
            result |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        dlat = ~(result >> 1) if (result & 1) else (result >> 1)
        lat += dlat

        shift = 0
        result = 0
        while True:
            if index >= len(polyline_str):
                break
            b = ord(polyline_str[index]) - 63
            index += 1
            result |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        dlng = ~(result >> 1) if (result & 1) else (result >> 1)
        lng += dlng

        coordinates.append({"latitude": lat / 1e5, "longitude": lng / 1e5})

    return coordinates


@router.get("/directions", response_model=ResponseModel)
def get_directions(
    origin_lat: float = Query(..., ge=-90, le=90),
    origin_lng: float = Query(..., ge=-180, le=180),
    destination_lat: float = Query(..., ge=-90, le=90),
    destination_lng: float = Query(..., ge=-180, le=180),
    mode: str = Query("driving"),
):
    """
    Returns Google Directions `routes` (server-side key).

    Mobile can render:
    - the route polyline (decoded)
    - turn-by-turn steps (plain text)
    """

    if not settings.GOOGLE_MAPS_API_KEY:
        raise HTTPException(status_code=500, detail="GOOGLE_MAPS_API_KEY is not configured")

    mode_normalized = (mode or "driving").lower().strip()
    # Keep it permissive but avoid obvious invalid values.
    if mode_normalized not in {"driving", "walking", "bicycling", "transit"}:
        mode_normalized = "driving"

    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": f"{origin_lat},{origin_lng}",
        "destination": f"{destination_lat},{destination_lng}",
        "mode": mode_normalized,
        "key": settings.GOOGLE_MAPS_API_KEY,
    }

    try:
        resp = requests.get(url, params=params, timeout=15)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to call Google Directions: {str(e)}")

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Google Directions failed: {resp.text[:500]}")

    payload = resp.json()
    if payload.get("status") != "OK":
        # Examples: ZERO_RESULTS, OVER_QUERY_LIMIT, REQUEST_DENIED, INVALID_REQUEST
        raise HTTPException(
            status_code=400,
            detail=f"Google Directions returned status={payload.get('status')}",
        )

    routes_out: List[Dict[str, Any]] = []
    routes = payload.get("routes", []) or []
    for r in routes:
        overview = r.get("overview_polyline", {}) or {}
        decoded_points = _decode_polyline(overview.get("points", "")) if overview.get("points") else []

        legs = r.get("legs", []) or []
        first_leg = legs[0] if legs else {}
        distance = first_leg.get("distance") or {}
        duration = first_leg.get("duration") or {}

        steps_raw = (first_leg.get("steps", []) or [])[:50]  # cap to keep payload small
        steps = []
        for s in steps_raw:
            steps.append(
                {
                    "instruction": _strip_html(s.get("html_instructions")),
                    "distanceText": (s.get("distance") or {}).get("text"),
                    "durationText": (s.get("duration") or {}).get("text"),
                }
            )

        routes_out.append(
            {
                "summary": r.get("summary"),
                "overviewPolylinePoints": overview.get("points"),
                "routePoints": decoded_points,
                "distanceText": distance.get("text"),
                "durationText": duration.get("text"),
                "steps": steps,
            }
        )

    return ResponseModel(
        success=True,
        data={
            "routes": routes_out,
            "copyrights": payload.get("routes", [{}])[0].get("copyrights"),
        },
        message="Directions retrieved successfully",
    )


@router.get("/reverse-geocode", response_model=ResponseModel)
def reverse_geocode(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
):
    """
    Reverse-geocode coordinates into address components using Google Geocoding API.
    This is used by the mobile app to autofill delivery address.
    """
    if not settings.GOOGLE_MAPS_API_KEY:
        raise HTTPException(status_code=500, detail="GOOGLE_MAPS_API_KEY is not configured")

    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "latlng": f"{lat},{lng}",
        "key": settings.GOOGLE_MAPS_API_KEY,
        "language": "en",
    }

    try:
        resp = requests.get(url, params=params, timeout=15)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to call Google Geocoding: {str(e)}")

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Google Geocoding failed: {resp.text[:500]}")

    payload = resp.json() if resp.content else {}
    if payload.get("status") != "OK":
        raise HTTPException(
            status_code=400,
            detail=f"Google Geocoding returned status={payload.get('status')}",
        )

    results = payload.get("results") or []
    if not results:
        raise HTTPException(status_code=404, detail="No address found for coordinates")

    top = results[0]
    formatted_address = top.get("formatted_address")

    components = top.get("address_components") or []

    postal_code: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    route: Optional[str] = None
    street_number: Optional[str] = None
    sublocality: Optional[str] = None

    for comp in components:
        types = comp.get("types") or []
        long_name = comp.get("long_name")
        if not long_name:
            continue

        if "postal_code" in types:
            postal_code = long_name
        if "locality" in types:
            city = long_name
        if "administrative_area_level_1" in types:
            state = long_name
        if "route" in types:
            route = long_name
        if "street_number" in types:
            street_number = long_name
        if "sublocality_level_1" in types:
            sublocality = long_name

    # Build best-effort address line 1.
    address_line1 = ""
    if street_number and route:
        address_line1 = f"{street_number} {route}"
    elif route:
        address_line1 = route

    if not address_line1 and isinstance(formatted_address, str):
        address_line1 = formatted_address

    address_line2 = sublocality or ""

    return ResponseModel(
        success=True,
        data={
            "address_line1": address_line1,
            "address_line2": address_line2,
            "city": city or "",
            "state": state or "",
            "pincode": postal_code or "",
            "formatted_address": formatted_address,
            "latitude": lat,
            "longitude": lng,
        },
        message="Location resolved successfully",
    )

