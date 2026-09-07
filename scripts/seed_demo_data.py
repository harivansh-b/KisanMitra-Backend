#!/usr/bin/env python3
"""
Seed demo application data for KisanMitra.

Creates realistic Maharashtra-based demo entities:
  - Users (farmers, FPOs, buyers)
  - Farmer profiles
  - FPO profiles
  - FPO memberships
  - Buyer profiles
  - Produce listings (linked to real crop IDs + mandi price reference)
  - Buyer requirements
  - Orders
  - Transactions

All entities are clearly labelled as demo data via auth_user_id prefix "demo-".
Safe to run multiple times (idempotent).
"""

import os
import sys
import uuid
import random
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./kisanmitra.db")

rng = random.Random(99)


# ---------------------------------------------------------------------------
# Demo entity definitions
# ---------------------------------------------------------------------------
DEMO_FARMERS = [
    # (auth_user_id, name, district, village, lat, lon, phone, farm_size)
    ("demo-farmer-001", "Ramesh Patil", "Nashik", "Lasalgaon", 20.1271, 74.0652, "9876500001", 4.5),
    ("demo-farmer-002", "Sunita Deshmukh", "Pune", "Junnar", 19.2039, 73.8811, "9876500002", 2.8),
    ("demo-farmer-003", "Maruti Jadhav", "Satara", "Karad", 17.2880, 74.1832, "9876500003", 6.0),
    ("demo-farmer-004", "Laxmi Kale", "Akola", "Akola Rural", 20.6913, 77.0019, "9876500004", 3.2),
    ("demo-farmer-005", "Vijay Shinde", "Nagpur", "Kamptee", 21.2167, 79.1869, "9876500005", 5.5),
    ("demo-farmer-006", "Kavita Bhosle", "Sangli", "Miraj", 16.8269, 74.6557, "9876500006", 3.0),
    ("demo-farmer-007", "Dnyaneshwar More", "Amravati", "Daryapur", 20.9258, 77.3224, "9876500007", 7.2),
    ("demo-farmer-008", "Rekha Tupe", "Solapur", "Pandharpur", 17.6846, 75.3288, "9876500008", 2.5),
]

DEMO_FPOS = [
    # (auth_user_id, org_name, reg_no, contact, district, village, lat, lon, phone)
    ("demo-fpo-001", "Nashik Farmers Producer Company Ltd", "MH-FPC-2019-001",
     "Govind Wani", "Nashik", "Niphad", 20.0721, 74.0898, "9876501001"),
    ("demo-fpo-002", "Vidarbha Agri Producer Organization", "MH-FPC-2020-002",
     "Sanjay Raut", "Amravati", "Amravati", 20.9320, 77.7523, "9876501002"),
    ("demo-fpo-003", "Pune District Farmer Cooperative", "MH-FPC-2021-003",
     "Anita Shah", "Pune", "Pune", 18.5204, 73.8567, "9876501003"),
]

DEMO_BUYERS = [
    # (auth_user_id, org_name, buyer_type, contact, district, phone, lat, lon)
    ("demo-buyer-001", "MahaFresh Foods Pvt Ltd", "WHOLESALER",
     "Suresh Mehta", "Pune", "9876502001", 18.5204, 73.8567),
    ("demo-buyer-002", "Sahyadri Agro Exports", "EXPORTER",
     "Priya Joshi", "Nashik", "9876502002", 19.9975, 73.7898),
    ("demo-buyer-003", "Nagpur Agri Processing Co", "PROCESSOR",
     "Rakesh Singh", "Nagpur", "9876502003", 21.1458, 79.0882),
]


def get_crop_id(conn, crop_name_like: str):
    """Find a crop by partial name match."""
    row = conn.execute(
        text("SELECT id FROM crops WHERE name ILIKE :name LIMIT 1"),
        {"name": f"%{crop_name_like}%"},
    ).fetchone()
    if row:
        return row[0]
    # Try case-insensitive for SQLite
    row = conn.execute(
        text("SELECT id FROM crops WHERE LOWER(name) LIKE :name LIMIT 1"),
        {"name": f"%{crop_name_like.lower()}%"},
    ).fetchone()
    return row[0] if row else None


def user_exists(conn, auth_user_id: str) -> str | None:
    row = conn.execute(
        text("SELECT id FROM users WHERE auth_user_id = :aid"),
        {"aid": auth_user_id},
    ).fetchone()
    return row[0] if row else None


def profile_exists(conn, table: str, user_id: str) -> bool:
    row = conn.execute(
        text(f"SELECT id FROM {table} WHERE user_id = :uid"),
        {"uid": user_id},
    ).fetchone()
    return row is not None


def wkt_point(lon, lat):
    if lon is None or lat is None:
        return None
    return f"SRID=4326;POINT({lon} {lat})"


def get_mandi_modal_price(conn, commodity_name: str, district: str = None) -> float | None:
    """Get latest modal price for a commodity to set realistic listing prices."""
    q = """
        SELECT mp.modal_price
        FROM mandi_prices mp
        JOIN mandis m ON mp.mandi_id = m.id
        WHERE LOWER(mp.commodity_name) LIKE :cn
        ORDER BY mp.arrival_date DESC
        LIMIT 1
    """
    params = {"cn": f"%{commodity_name.lower()}%"}
    row = conn.execute(text(q), params).fetchone()
    return float(row[0]) if row else None


def seed_users_and_profiles(conn, is_pg: bool):
    inserted = 0

    # --- Farmers ---
    for auth_id, name, district, village, lat, lon, phone, farm_size in DEMO_FARMERS:
        user_id = user_exists(conn, auth_id)
        if not user_id:
            user_id = str(uuid.uuid4())
            conn.execute(
                text("""
                    INSERT INTO users (id, auth_user_id, role, phone, email, is_active)
                    VALUES (:id, :aid, 'FARMER', :phone,
                            :email, TRUE)
                """),
                {"id": user_id, "aid": auth_id, "phone": phone,
                 "email": f"{auth_id}@demo.kisanmitra.in"},
            )
            inserted += 1

        if not profile_exists(conn, "farmer_profiles", user_id):
            loc = wkt_point(lon, lat) if is_pg else None
            if is_pg:
                conn.execute(
                    text("""
                        INSERT INTO farmer_profiles
                            (id, user_id, name, phone, village, district, state,
                             latitude, longitude, location, farm_size, verification_status)
                        VALUES (:id, :uid, :name, :phone, :village, :district, 'Maharashtra',
                                :lat, :lon, ST_GeogFromText(:loc), :fs, 'VERIFIED')
                    """),
                    {"id": str(uuid.uuid4()), "uid": user_id, "name": name, "phone": phone,
                     "village": village, "district": district, "lat": lat, "lon": lon,
                     "loc": loc, "fs": farm_size},
                )
            else:
                conn.execute(
                    text("""
                        INSERT INTO farmer_profiles
                            (id, user_id, name, phone, village, district, state,
                             latitude, longitude, farm_size, verification_status)
                        VALUES (:id, :uid, :name, :phone, :village, :district, 'Maharashtra',
                                :lat, :lon, :fs, 'VERIFIED')
                    """),
                    {"id": str(uuid.uuid4()), "uid": user_id, "name": name, "phone": phone,
                     "village": village, "district": district, "lat": lat, "lon": lon, "fs": farm_size},
                )

    # --- FPOs ---
    fpo_user_ids = {}
    for auth_id, org_name, reg_no, contact, district, village, lat, lon, phone in DEMO_FPOS:
        user_id = user_exists(conn, auth_id)
        if not user_id:
            user_id = str(uuid.uuid4())
            conn.execute(
                text("""
                    INSERT INTO users (id, auth_user_id, role, phone, email, is_active)
                    VALUES (:id, :aid, 'FPO', :phone, :email, TRUE)
                """),
                {"id": user_id, "aid": auth_id, "phone": phone,
                 "email": f"{auth_id}@demo.kisanmitra.in"},
            )
            inserted += 1
        fpo_user_ids[auth_id] = user_id

        if not profile_exists(conn, "fpo_profiles", user_id):
            loc = wkt_point(lon, lat) if is_pg else None
            if is_pg:
                conn.execute(
                    text("""
                        INSERT INTO fpo_profiles
                            (id, user_id, organization_name, registration_number,
                             contact_person, phone, email, village_or_city, district, state,
                             latitude, longitude, location, verification_status)
                        VALUES (:id, :uid, :org, :reg, :contact, :phone, :email,
                                :village, :district, 'Maharashtra',
                                :lat, :lon, ST_GeogFromText(:loc), 'VERIFIED')
                    """),
                    {"id": str(uuid.uuid4()), "uid": user_id, "org": org_name,
                     "reg": reg_no, "contact": contact, "phone": phone,
                     "email": f"{auth_id}@demo.kisanmitra.in",
                     "village": village, "district": district,
                     "lat": lat, "lon": lon, "loc": loc},
                )
            else:
                conn.execute(
                    text("""
                        INSERT INTO fpo_profiles
                            (id, user_id, organization_name, registration_number,
                             contact_person, phone, email, village_or_city, district, state,
                             latitude, longitude, verification_status)
                        VALUES (:id, :uid, :org, :reg, :contact, :phone, :email,
                                :village, :district, 'Maharashtra',
                                :lat, :lon, 'VERIFIED')
                    """),
                    {"id": str(uuid.uuid4()), "uid": user_id, "org": org_name,
                     "reg": reg_no, "contact": contact, "phone": phone,
                     "email": f"{auth_id}@demo.kisanmitra.in",
                     "village": village, "district": district, "lat": lat, "lon": lon},
                )

    # --- Buyers ---
    buyer_user_ids = {}
    for auth_id, org_name, buyer_type, contact, district, phone, lat, lon in DEMO_BUYERS:
        user_id = user_exists(conn, auth_id)
        if not user_id:
            user_id = str(uuid.uuid4())
            conn.execute(
                text("""
                    INSERT INTO users (id, auth_user_id, role, phone, email, is_active)
                    VALUES (:id, :aid, 'BUYER', :phone, :email, TRUE)
                """),
                {"id": user_id, "aid": auth_id, "phone": phone,
                 "email": f"{auth_id}@demo.kisanmitra.in"},
            )
            inserted += 1
        buyer_user_ids[auth_id] = user_id

        if not profile_exists(conn, "buyer_profiles", user_id):
            loc = wkt_point(lon, lat) if is_pg else None
            if is_pg:
                conn.execute(
                    text("""
                        INSERT INTO buyer_profiles
                            (id, user_id, organization_name, buyer_type, contact_person,
                             phone, email, location_name, latitude, longitude,
                             location, verification_status)
                        VALUES (:id, :uid, :org, :bt, :contact,
                                :phone, :email, :loc_name, :lat, :lon,
                                ST_GeogFromText(:loc), 'VERIFIED')
                    """),
                    {"id": str(uuid.uuid4()), "uid": user_id, "org": org_name,
                     "bt": buyer_type, "contact": contact, "phone": phone,
                     "email": f"{auth_id}@demo.kisanmitra.in",
                     "loc_name": district, "lat": lat, "lon": lon, "loc": loc},
                )
            else:
                conn.execute(
                    text("""
                        INSERT INTO buyer_profiles
                            (id, user_id, organization_name, buyer_type, contact_person,
                             phone, email, location_name, latitude, longitude, verification_status)
                        VALUES (:id, :uid, :org, :bt, :contact,
                                :phone, :email, :loc_name, :lat, :lon, 'VERIFIED')
                    """),
                    {"id": str(uuid.uuid4()), "uid": user_id, "org": org_name,
                     "bt": buyer_type, "contact": contact, "phone": phone,
                     "email": f"{auth_id}@demo.kisanmitra.in",
                     "loc_name": district, "lat": lat, "lon": lon},
                )

    return inserted, fpo_user_ids, buyer_user_ids


def seed_listings(conn, is_pg: bool):
    """Create produce listings from demo farmer accounts."""
    inserted = 0

    farmer_listings = [
        # (farmer_auth_id, crop_like, variety, qty_qtl, district)
        ("demo-farmer-001", "Onion", "Nashik Red", 50.0, "Nashik", 18.4969, 73.8497),
        ("demo-farmer-002", "Tomato", "Hybrid Red", 30.0, "Pune", 19.2039, 73.8811),
        ("demo-farmer-003", "Soybean", "JS 335", 40.0, "Satara", 17.2880, 74.1832),
        ("demo-farmer-004", "Cotton", "Bt Cotton", 25.0, "Akola", 20.6913, 77.0019),
        ("demo-farmer-005", "Wheat", "Lokwan", 60.0, "Nagpur", 21.2167, 79.1869),
        ("demo-farmer-006", "Turmeric", "Sangli", 20.0, "Sangli", 16.8524, 74.5648),
        ("demo-farmer-007", "Cotton", "Bt Cotton", 35.0, "Amravati", 20.9320, 77.7523),
        ("demo-farmer-008", "Soybean", "Local", 45.0, "Solapur", 17.6599, 75.9064),
    ]

    for farmer_auth, crop_like, variety, qty, district, lat, lon in farmer_listings:
        # Get farmer user_id
        row = conn.execute(
            text("SELECT id FROM users WHERE auth_user_id = :aid"),
            {"aid": farmer_auth},
        ).fetchone()
        if not row:
            continue
        farmer_user_id = row[0]

        # Check if listing already exists
        existing = conn.execute(
            text("""
                SELECT id FROM produce_listings
                WHERE seller_id = :sid AND variety = :var
            """),
            {"sid": farmer_user_id, "var": variety},
        ).fetchone()
        if existing:
            continue

        crop_id = get_crop_id(conn, crop_like)
        if not crop_id:
            print(f"  [WARNING] Crop not found: {crop_like} — skipping listing")
            continue

        # Try to set price near mandi modal price
        modal = get_mandi_modal_price(conn, crop_like, district)
        if modal:
            expected_price = round(modal * rng.uniform(0.95, 1.05))
            min_price = round(modal * 0.90)
        else:
            expected_price = 2000
            min_price = 1800

        harvest_date = date.today() - timedelta(days=rng.randint(5, 20))
        available_until = datetime.now() + timedelta(days=rng.randint(15, 45))

        loc_val = wkt_point(lon, lat) if is_pg else None

        if is_pg:
            conn.execute(
                text("""
                    INSERT INTO produce_listings
                        (id, seller_id, seller_type, crop_id, variety, quantity, unit,
                         quality_grade, harvest_date, expected_price, min_price,
                         location_name, latitude, longitude, location,
                         status, available_until)
                    VALUES
                        (:id, :sid, 'FARMER', :cid, :var, :qty, 'QUINTAL',
                         'GRADE_A', :hd, :ep, :mp,
                         :loc_name, :lat, :lon, ST_GeogFromText(:loc),
                         'ACTIVE', :au)
                """),
                {"id": str(uuid.uuid4()), "sid": farmer_user_id, "cid": crop_id,
                 "var": variety, "qty": qty, "hd": harvest_date,
                 "ep": expected_price, "mp": min_price,
                 "loc_name": district, "lat": lat, "lon": lon, "loc": loc_val,
                 "au": available_until},
            )
        else:
            conn.execute(
                text("""
                    INSERT INTO produce_listings
                        (id, seller_id, seller_type, crop_id, variety, quantity, unit,
                         quality_grade, harvest_date, expected_price, min_price,
                         location_name, latitude, longitude, status, available_until)
                    VALUES
                        (:id, :sid, 'FARMER', :cid, :var, :qty, 'QUINTAL',
                         'GRADE_A', :hd, :ep, :mp,
                         :loc_name, :lat, :lon, 'ACTIVE', :au)
                """),
                {"id": str(uuid.uuid4()), "sid": farmer_user_id, "cid": crop_id,
                 "var": variety, "qty": qty, "hd": harvest_date,
                 "ep": expected_price, "mp": min_price,
                 "loc_name": district, "lat": lat, "lon": lon,
                 "au": available_until},
            )
        inserted += 1

    return inserted


def seed_requirements(conn, is_pg: bool):
    """Create buyer requirements."""
    inserted = 0

    buyer_requirements = [
        ("demo-buyer-001", "Onion", "Nashik Red", 200.0, "Pune", 18.5204, 73.8567),
        ("demo-buyer-001", "Tomato", "Hybrid Red", 100.0, "Pune", 18.5204, 73.8567),
        ("demo-buyer-002", "Grape", "Thompson Seedless", 50.0, "Nashik", 19.9975, 73.7898),
        ("demo-buyer-002", "Pomegranate", "Bhagwa", 75.0, "Nashik", 19.9975, 73.7898),
        ("demo-buyer-003", "Cotton", "Bt Cotton", 150.0, "Nagpur", 21.1458, 79.0882),
        ("demo-buyer-003", "Soybean", "JS 335", 200.0, "Nagpur", 21.1458, 79.0882),
    ]

    for buyer_auth, crop_like, variety, qty, district, lat, lon in buyer_requirements:
        row = conn.execute(
            text("SELECT id FROM users WHERE auth_user_id = :aid"),
            {"aid": buyer_auth},
        ).fetchone()
        if not row:
            continue
        buyer_user_id = row[0]

        # Check if already exists
        existing = conn.execute(
            text("""
                SELECT id FROM buyer_requirements
                WHERE buyer_id = :bid AND variety = :var
            """),
            {"bid": buyer_user_id, "var": variety},
        ).fetchone()
        if existing:
            continue

        crop_id = get_crop_id(conn, crop_like)
        if not crop_id:
            continue

        modal = get_mandi_modal_price(conn, crop_like, district)
        target_price = round((modal or 2000) * rng.uniform(1.02, 1.10))
        required_until = datetime.now() + timedelta(days=rng.randint(20, 60))

        if is_pg:
            conn.execute(
                text("""
                    INSERT INTO buyer_requirements
                        (id, buyer_id, crop_id, variety, required_quantity, unit,
                         quality_grade, target_price, delivery_location, latitude, longitude,
                         location, required_until, status)
                    VALUES
                        (:id, :bid, :cid, :var, :qty, 'QUINTAL',
                         'GRADE_A', :tp, :dloc, :lat, :lon,
                         ST_GeogFromText(:loc), :ru, 'ACTIVE')
                """),
                {"id": str(uuid.uuid4()), "bid": buyer_user_id, "cid": crop_id,
                 "var": variety, "qty": qty, "tp": target_price,
                 "dloc": district, "lat": lat, "lon": lon,
                 "loc": wkt_point(lon, lat), "ru": required_until},
            )
        else:
            conn.execute(
                text("""
                    INSERT INTO buyer_requirements
                        (id, buyer_id, crop_id, variety, required_quantity, unit,
                         quality_grade, target_price, delivery_location, latitude, longitude,
                         required_until, status)
                    VALUES
                        (:id, :bid, :cid, :var, :qty, 'QUINTAL',
                         'GRADE_A', :tp, :dloc, :lat, :lon, :ru, 'ACTIVE')
                """),
                {"id": str(uuid.uuid4()), "bid": buyer_user_id, "cid": crop_id,
                 "var": variety, "qty": qty, "tp": target_price,
                 "dloc": district, "lat": lat, "lon": lon, "ru": required_until},
            )
        inserted += 1

    return inserted


def seed_orders_and_transactions(conn):
    """Create sample orders linking farmer listings to buyer requirements."""
    inserted = 0

    # Get a buyer user
    buyer_row = conn.execute(
        text("SELECT id FROM users WHERE auth_user_id = 'demo-buyer-001'"),
    ).fetchone()
    if not buyer_row:
        return 0
    buyer_id = buyer_row[0]

    # Get some active listings
    listings = conn.execute(
        text("""
            SELECT pl.id, pl.seller_id, pl.expected_price, pl.quantity
            FROM produce_listings pl
            WHERE pl.status = 'ACTIVE'
            LIMIT 3
        """),
    ).fetchall()

    for listing_id, seller_id, expected_price, qty in listings:
        # Check if order already exists
        existing = conn.execute(
            text("SELECT id FROM orders WHERE listing_id = :lid AND buyer_id = :bid"),
            {"lid": listing_id, "bid": buyer_id},
        ).fetchone()
        if existing:
            continue

        order_qty = round(qty * 0.5)
        agreed_price = round(expected_price * 0.98)
        total_amount = round(order_qty * agreed_price)
        order_id = str(uuid.uuid4())

        conn.execute(
            text("""
                INSERT INTO orders
                    (id, buyer_id, seller_id, listing_id, quantity,
                     agreed_price, total_amount, status, notes)
                VALUES
                    (:id, :bid, :sid, :lid, :qty,
                     :ap, :ta, 'CONFIRMED', 'Demo order created by seed script')
            """),
            {"id": order_id, "bid": buyer_id, "sid": seller_id,
             "lid": listing_id, "qty": order_qty, "ap": agreed_price, "ta": total_amount},
        )

        # Create transaction
        conn.execute(
            text("""
                INSERT INTO transactions
                    (id, order_id, amount, status, payment_method, notes)
                VALUES
                    (:id, :oid, :amt, 'SETTLED', 'BANK_TRANSFER', 'Demo transaction')
            """),
            {"id": str(uuid.uuid4()), "oid": order_id, "amt": total_amount},
        )
        inserted += 1

    return inserted


def main():
    print("=" * 60)
    print("KisanMitra - Demo Application Data Seed")
    print("=" * 60)

    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    is_pg = engine.dialect.name == "postgresql"

    with engine.connect() as conn:
        print("\n-> Seeding users and profiles...")
        n_users, fpo_ids, buyer_ids = seed_users_and_profiles(conn, is_pg)
        conn.commit()
        print(f"  [OK] Users inserted: {n_users}")

        print("\n-> Seeding produce listings...")
        n_listings = seed_listings(conn, is_pg)
        conn.commit()
        print(f"  [OK] Listings inserted: {n_listings}")

        print("\n-> Seeding buyer requirements...")
        n_reqs = seed_requirements(conn, is_pg)
        conn.commit()
        print(f"  [OK] Requirements inserted: {n_reqs}")

        print("\n-> Seeding orders and transactions...")
        try:
            n_orders = seed_orders_and_transactions(conn)
            conn.commit()
            print(f"  [OK] Orders inserted: {n_orders}")
        except Exception as e:
            print(f"  [WARN] Orders seed skipped: {e}")
            conn.rollback()

    print("\n[OK] Demo data seed complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()
