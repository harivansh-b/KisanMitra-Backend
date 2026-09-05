import re
from typing import Optional


def validate_phone(phone: Optional[str]) -> Optional[str]:
    if not phone:
        return None
    cleaned = re.sub(r"[^\d+]", "", phone)
    if cleaned.startswith("+91"):
        cleaned = cleaned[3:]
    if cleaned.startswith("0"):
        cleaned = cleaned[1:]
    if not re.match(r"^[6-9]\d{9}$", cleaned):
        raise ValueError("Invalid Indian phone number. Expected 10 digits starting with 6-9.")
    return cleaned


def validate_pincode(pincode: Optional[str]) -> Optional[str]:
    if not pincode:
        return None
    cleaned = pincode.strip()
    if not re.match(r"^[1-9][0-9]{5}$", cleaned):
        raise ValueError("Invalid Indian pincode. Expected 6 digits not starting with 0.")
    return cleaned


def validate_lat_long(lat: Optional[float], lon: Optional[float]) -> None:
    if lat is not None and not (-90.0 <= lat <= 90.0):
        raise ValueError("Latitude must be between -90 and 90 degrees.")
    if lon is not None and not (-180.0 <= lon <= 180.0):
        raise ValueError("Longitude must be between -180 and 180 degrees.")
