"""Authenticated, map-safe participant discovery."""
from math import asin, cos, radians, sin, sqrt
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.buyer import BuyerProfile
from app.models.farmer import FarmerProfile
from app.models.fpo import FPOProfile
from app.models.user import User

router = APIRouter(prefix="/directory", tags=["Participant Directory"])


def distance_km(latitude: float, longitude: float, other_latitude: float, other_longitude: float) -> float:
    """Great-circle distance, adequate for filtering the small returned profile set."""
    lat1, lon1, lat2, lon2 = map(radians, (latitude, longitude, other_latitude, other_longitude))
    a = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return 6371 * 2 * asin(sqrt(a))


MAHARASHTRA_DISTRICT_COORDS = {
    "Pune": (18.5204, 73.8567),
    "Nashik": (19.9975, 73.7898),
    "Mumbai": (19.0760, 72.8777),
    "Nagpur": (21.1458, 79.0882),
    "Chhatrapati Sambhajinagar": (19.8762, 75.3433),
    "Solapur": (17.6599, 75.9064),
    "Kolhapur": (16.7050, 74.2433),
    "Amravati": (20.9374, 77.7796),
    "Latur": (18.4088, 76.5604),
    "Satara": (17.6805, 74.0183),
    "Ahmednagar": (19.0948, 74.7480),
    "Jalgaon": (21.0077, 75.5626),
}


@router.get("/nearby")
def nearby_participants(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(100, ge=1, le=500),
    participant_types: list[Literal["FARMER", "BUYER", "FPO", "STORAGE", "TRANSPORT", "QUALITY"]] = Query(["FARMER", "BUYER", "FPO", "STORAGE", "TRANSPORT", "QUALITY"]),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return minimal profile data for signed-in marketplace discovery, never contact details."""
    results: list[dict] = []
    sources = []
    if "FARMER" in participant_types:
        sources.append(("FARMER", db.query(FarmerProfile).filter(FarmerProfile.latitude.isnot(None), FarmerProfile.longitude.isnot(None)).all()))
    if any(t in participant_types for t in ["BUYER", "STORAGE", "TRANSPORT", "QUALITY"]):
        sources.append(("BUYER", db.query(BuyerProfile).filter(BuyerProfile.latitude.isnot(None), BuyerProfile.longitude.isnot(None)).all()))
    if "FPO" in participant_types:
        sources.append(("FPO", db.query(FPOProfile).filter(FPOProfile.latitude.isnot(None), FPOProfile.longitude.isnot(None)).all()))
    for participant_type, profiles in sources:
        for profile in profiles:
            if profile.user_id == current_user.id:
                continue
            distance = distance_km(latitude, longitude, profile.latitude, profile.longitude)
            if distance > radius_km:
                continue
            name = profile.name if participant_type == "FARMER" else profile.organization_name
            location_name = profile.village if participant_type == "FARMER" else (getattr(profile, "location_name", None) or getattr(profile, "village_or_city", None))
            results.append({
                "id": profile.id, "participant_type": participant_type, "name": name,
                "location_name": location_name, "district": getattr(profile, "district", "Pune"),
                "state": getattr(profile, "state", "Maharashtra"),
                "latitude": profile.latitude, "longitude": profile.longitude,
                "verification_status": profile.verification_status, "distance_km": round(distance, 1),
            })
    return sorted(results, key=lambda item: item["distance_km"])


@router.get("/map-users")
def get_map_users(
    district: str | None = Query(None),
    role: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """Returns all non-admin users across Maharashtra with map coordinates for display."""
    users_list = []
    
    # Farmers
    farmers = db.query(FarmerProfile).all()
    for f in farmers:
        if role and role.upper() != "FARMER":
            continue
        dist = f.district or "Pune"
        if district and district.lower() != dist.lower():
            continue
        lat = f.latitude or MAHARASHTRA_DISTRICT_COORDS.get(dist, (18.5204, 73.8567))[0]
        lng = f.longitude or MAHARASHTRA_DISTRICT_COORDS.get(dist, (18.5204, 73.8567))[1]
        users_list.append({
            "id": f.id,
            "name": f.name,
            "role": "FARMER",
            "district": dist,
            "state": f.state or "Maharashtra",
            "latitude": lat,
            "longitude": lng,
            "verification_status": f.verification_status,
        })
        
    # FPOs
    fpos = db.query(FPOProfile).all()
    for fp in fpos:
        if role and role.upper() != "FPO":
            continue
        dist = fp.district or "Nashik"
        if district and district.lower() != dist.lower():
            continue
        lat = fp.latitude or MAHARASHTRA_DISTRICT_COORDS.get(dist, (19.9975, 73.7898))[0]
        lng = fp.longitude or MAHARASHTRA_DISTRICT_COORDS.get(dist, (19.9975, 73.7898))[1]
        users_list.append({
            "id": fp.id,
            "name": fp.organization_name,
            "role": "FPO",
            "district": dist,
            "state": fp.state or "Maharashtra",
            "latitude": lat,
            "longitude": lng,
            "verification_status": fp.verification_status,
        })

    # Buyers, Storage, Transport, Quality
    buyers = db.query(BuyerProfile).all()
    for b in buyers:
        assigned_role = getattr(b, "user", None).role.value if getattr(b, "user", None) and hasattr(getattr(b, "user", None), "role") else "BUYER"
        if assigned_role == "ADMIN":
            continue
        if role and role.upper() != assigned_role.upper():
            continue
        dist = getattr(b, "district", None) or "Mumbai"
        if district and district.lower() != dist.lower():
            continue
        lat = b.latitude or MAHARASHTRA_DISTRICT_COORDS.get(dist, (19.0760, 72.8777))[0]
        lng = b.longitude or MAHARASHTRA_DISTRICT_COORDS.get(dist, (19.0760, 72.8777))[1]
        users_list.append({
            "id": b.id,
            "name": b.organization_name,
            "role": assigned_role,
            "district": dist,
            "state": getattr(b, "state", "Maharashtra"),
            "latitude": lat,
            "longitude": lng,
            "verification_status": b.verification_status,
        })

    return {"users": users_list, "total": len(users_list), "state": "Maharashtra"}

