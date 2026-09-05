import math
from typing import Optional
from sqlalchemy import func
from geoalchemy2.elements import WKTElement


class GeoService:
    @staticmethod
    def create_point_wkt(latitude: Optional[float], longitude: Optional[float]) -> Optional[WKTElement]:
        """Creates a PostGIS WKTElement with SRID 4326 (POINT(lon lat))."""
        if latitude is None or longitude is None:
            return None
        return WKTElement(f"POINT({longitude} {latitude})", srid=4326)

    @staticmethod
    def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate the great-circle distance between two points on the Earth in kilometers."""
        R = 6371.0  # Earth's radius in km
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (
            math.sin(dlat / 2.0) ** 2
            + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2
        )
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return R * c

    @staticmethod
    def apply_radius_filter(query, model, latitude: float, longitude: float, radius_km: float, is_postgresql: bool = True):
        """
        Applies a spatial radius filter on a model.
        In PostgreSQL: utilizes PostGIS ST_DWithin with spatial index.
        In SQLite/Fallback: uses bounding-box approximation on lat/lon columns.
        """
        if is_postgresql:
            # PostGIS ST_DWithin takes meters on geography
            point = func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326)
            return query.filter(func.ST_DWithin(model.location, point, radius_km * 1000.0))
        else:
            # Bounding box approximation (~111 km per degree latitude)
            lat_deg = radius_km / 111.0
            lon_deg = radius_km / (111.0 * max(math.cos(math.radians(latitude)), 0.01))
            return query.filter(
                model.latitude.between(latitude - lat_deg, latitude + lat_deg),
                model.longitude.between(longitude - lon_deg, longitude + lon_deg),
            )


geo_service = GeoService()
