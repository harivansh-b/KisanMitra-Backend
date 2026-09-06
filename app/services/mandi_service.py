import math
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, text
from sqlalchemy.orm import Session, joinedload
from geoalchemy2.elements import WKTElement

from app.core.exceptions import NotFoundException
from app.models.crop import Crop
from app.models.mandi import Mandi
from app.models.mandi_price import MandiPrice
from app.schemas.mandi import MandiCreate, MandiPriceCreate, MandiPriceFilter


class MandiService:

    # ------------------------------------------------------------------
    # Mandi CRUD
    # ------------------------------------------------------------------

    @staticmethod
    def get_mandi_by_id(db: Session, mandi_id: str) -> Mandi:
        mandi = db.query(Mandi).filter(Mandi.id == mandi_id).first()
        if not mandi:
            raise NotFoundException(f"Mandi with ID '{mandi_id}' not found")
        return mandi

    @staticmethod
    def list_mandis(
        db: Session,
        district: Optional[str] = None,
        state: Optional[str] = None,
        is_active: Optional[bool] = True,
        offset: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Mandi], int]:
        query = db.query(Mandi)
        if is_active is not None:
            query = query.filter(Mandi.is_active == is_active)
        if state:
            query = query.filter(Mandi.state.ilike(f"%{state}%"))
        if district:
            query = query.filter(Mandi.district.ilike(f"%{district}%"))

        total = query.count()
        mandis = query.order_by(Mandi.district.asc(), Mandi.name.asc()).offset(offset).limit(limit).all()
        return mandis, total

    # ------------------------------------------------------------------
    # Price queries
    # ------------------------------------------------------------------

    @staticmethod
    def list_prices(
        db: Session,
        filters: MandiPriceFilter,
        offset: int = 0,
        limit: int = 50,
    ) -> Tuple[List[MandiPrice], int]:
        query = db.query(MandiPrice).options(joinedload(MandiPrice.mandi))

        if filters.mandi_id:
            query = query.filter(MandiPrice.mandi_id == filters.mandi_id)
        if filters.district:
            query = query.join(Mandi).filter(Mandi.district.ilike(f"%{filters.district}%"))
        if filters.commodity:
            query = query.filter(MandiPrice.commodity_name.ilike(f"%{filters.commodity}%"))
        if filters.variety:
            query = query.filter(MandiPrice.variety.ilike(f"%{filters.variety}%"))
        if filters.from_date:
            query = query.filter(MandiPrice.arrival_date >= filters.from_date)
        if filters.to_date:
            query = query.filter(MandiPrice.arrival_date <= filters.to_date)
        if filters.min_price is not None:
            query = query.filter(MandiPrice.modal_price >= filters.min_price)
        if filters.max_price is not None:
            query = query.filter(MandiPrice.modal_price <= filters.max_price)

        total = query.count()
        prices = (
            query.order_by(MandiPrice.arrival_date.desc(), MandiPrice.commodity_name.asc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return prices, total

    @staticmethod
    def list_mandi_prices(
        db: Session,
        mandi_id: str,
        offset: int = 0,
        limit: int = 50,
    ) -> Tuple[List[MandiPrice], int]:
        query = (
            db.query(MandiPrice)
            .options(joinedload(MandiPrice.mandi))
            .filter(MandiPrice.mandi_id == mandi_id)
        )
        total = query.count()
        prices = (
            query.order_by(MandiPrice.arrival_date.desc(), MandiPrice.commodity_name.asc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return prices, total

    @staticmethod
    def latest_prices(
        db: Session,
        commodity: Optional[str] = None,
        district: Optional[str] = None,
        limit: int = 100,
    ) -> List[MandiPrice]:
        """
        Return the most recent price record per (mandi, commodity_name) combination.
        Uses a subquery to get max arrival_date per group, then fetches records.
        """
        # Build subquery for max date per mandi+commodity
        subq = (
            db.query(
                MandiPrice.mandi_id,
                MandiPrice.commodity_name,
                func.max(MandiPrice.arrival_date).label("max_date"),
            )
            .group_by(MandiPrice.mandi_id, MandiPrice.commodity_name)
            .subquery()
        )

        query = (
            db.query(MandiPrice)
            .options(joinedload(MandiPrice.mandi))
            .join(
                subq,
                (MandiPrice.mandi_id == subq.c.mandi_id)
                & (MandiPrice.commodity_name == subq.c.commodity_name)
                & (MandiPrice.arrival_date == subq.c.max_date),
            )
        )

        if commodity:
            query = query.filter(MandiPrice.commodity_name.ilike(f"%{commodity}%"))
        if district:
            query = query.join(Mandi, MandiPrice.mandi_id == Mandi.id).filter(
                Mandi.district.ilike(f"%{district}%")
            )

        return (
            query.order_by(MandiPrice.commodity_name.asc(), MandiPrice.modal_price.desc())
            .limit(limit)
            .all()
        )

    # ------------------------------------------------------------------
    # Nearby mandis (PostGIS)
    # ------------------------------------------------------------------

    @staticmethod
    def nearby_mandis(
        db: Session,
        latitude: float,
        longitude: float,
        radius_km: float = 50.0,
        commodity: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Find nearby mandis using PostGIS ST_DWithin on geography column.
        Falls back to bounding-box approximation if not PostgreSQL.
        """
        is_pg = db.bind.dialect.name == "postgresql"  # type: ignore[union-attr]

        if is_pg:
            point = func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326)
            distance_expr = func.ST_Distance(Mandi.location, point)

            query = (
                db.query(Mandi, distance_expr.label("distance_m"))
                .filter(
                    Mandi.is_active == True,
                    func.ST_DWithin(Mandi.location, point, radius_km * 1000.0),
                )
            )
        else:
            # Bounding box fallback for SQLite
            lat_deg = radius_km / 111.0
            lon_deg = radius_km / (111.0 * max(math.cos(math.radians(latitude)), 0.01))
            query = (
                db.query(Mandi, None)
                .filter(
                    Mandi.is_active == True,
                    Mandi.latitude.isnot(None),
                    Mandi.longitude.isnot(None),
                    Mandi.latitude.between(latitude - lat_deg, latitude + lat_deg),
                    Mandi.longitude.between(longitude - lon_deg, longitude + lon_deg),
                )
            )

        if commodity:
            # Only return mandis that have prices for this commodity
            query = query.join(MandiPrice, Mandi.id == MandiPrice.mandi_id).filter(
                MandiPrice.commodity_name.ilike(f"%{commodity}%")
            ).distinct()

        results = query.order_by(text("distance_m ASC") if is_pg else Mandi.name.asc()).limit(limit).all()

        output = []
        for row in results:
            if is_pg:
                mandi, dist_m = row
                dist_km = round((dist_m or 0) / 1000.0, 2)
            else:
                mandi = row[0]
                dist_km = 0.0
                if mandi.latitude is not None and mandi.longitude is not None:
                    dist_km = MandiService._haversine(latitude, longitude, mandi.latitude, mandi.longitude)
            output.append({"mandi": mandi, "distance_km": dist_km})
        return output

    @staticmethod
    def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
        return round(R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)), 2)

    # ------------------------------------------------------------------
    # Upsert price
    # ------------------------------------------------------------------

    @staticmethod
    def upsert_price(db: Session, data: MandiPriceCreate) -> MandiPrice:
        """
        Insert or update a mandi price record.
        Uses ON CONFLICT DO UPDATE for PostgreSQL, fallback insert for others.
        """
        is_pg = db.bind.dialect.name == "postgresql"  # type: ignore[union-attr]

        if is_pg:
            from sqlalchemy.dialects.postgresql import insert as pg_insert

            stmt = pg_insert(MandiPrice).values(
                id=str(__import__("uuid").uuid4()),
                mandi_id=data.mandi_id,
                commodity_id=data.commodity_id,
                commodity_name=data.commodity_name,
                variety=data.variety,
                grade=data.grade,
                arrival_date=data.arrival_date,
                arrival_quantity=data.arrival_quantity,
                arrival_unit=data.arrival_unit,
                min_price=data.min_price,
                max_price=data.max_price,
                modal_price=data.modal_price,
                price_unit=data.price_unit,
                source=data.source,
                source_record_id=data.source_record_id,
            ).on_conflict_do_update(
                constraint="uq_mandi_price_record",
                set_={
                    "min_price": data.min_price,
                    "max_price": data.max_price,
                    "modal_price": data.modal_price,
                    "arrival_quantity": data.arrival_quantity,
                    "commodity_id": data.commodity_id,
                    "source_record_id": data.source_record_id,
                },
            )
            db.execute(stmt)
            db.commit()

            record = (
                db.query(MandiPrice)
                .filter(
                    MandiPrice.mandi_id == data.mandi_id,
                    MandiPrice.commodity_name == data.commodity_name,
                    MandiPrice.variety == data.variety,
                    MandiPrice.grade == data.grade,
                    MandiPrice.arrival_date == data.arrival_date,
                    MandiPrice.source == data.source,
                )
                .first()
            )
            return record  # type: ignore[return-value]

        else:
            # SQLite fallback: check-then-insert
            existing = (
                db.query(MandiPrice)
                .filter(
                    MandiPrice.mandi_id == data.mandi_id,
                    MandiPrice.commodity_name == data.commodity_name,
                    MandiPrice.variety == data.variety,
                    MandiPrice.grade == data.grade,
                    MandiPrice.arrival_date == data.arrival_date,
                    MandiPrice.source == data.source,
                )
                .first()
            )
            if existing:
                existing.min_price = data.min_price
                existing.max_price = data.max_price
                existing.modal_price = data.modal_price
                existing.arrival_quantity = data.arrival_quantity
                db.commit()
                db.refresh(existing)
                return existing
            else:
                record = MandiPrice(**data.model_dump())
                db.add(record)
                db.commit()
                db.refresh(record)
                return record

    # ------------------------------------------------------------------
    # Commodity mapping helper
    # ------------------------------------------------------------------

    @staticmethod
    def find_crop_id(db: Session, commodity_name: str) -> Optional[str]:
        """Try to map a commodity name to a crop ID."""
        crop = db.query(Crop).filter(Crop.name.ilike(f"%{commodity_name}%")).first()
        return crop.id if crop else None


mandi_service = MandiService()
