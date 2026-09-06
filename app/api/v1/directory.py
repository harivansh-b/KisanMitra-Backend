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


@router.get("/nearby")
def nearby_participants(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(100, ge=1, le=500),
    participant_types: list[Literal["FARMER", "BUYER", "FPO"]] = Query(["FARMER", "BUYER", "FPO"]),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return minimal profile data for signed-in marketplace discovery, never contact details."""
    results: list[dict] = []
    sources = []
    if "FARMER" in participant_types:
        sources.append(("FARMER", db.query(FarmerProfile).filter(FarmerProfile.latitude.isnot(None), FarmerProfile.longitude.isnot(None)).all()))
    if "BUYER" in participant_types:
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
            location_name = profile.village if participant_type == "FARMER" else (profile.location_name if participant_type == "BUYER" else profile.village_or_city)
            results.append({
                "id": profile.id, "participant_type": participant_type, "name": name,
                "location_name": location_name, "district": profile.district,
                "latitude": profile.latitude, "longitude": profile.longitude,
                "verification_status": profile.verification_status, "distance_km": round(distance, 1),
            })
    return sorted(results, key=lambda item: item["distance_km"])
