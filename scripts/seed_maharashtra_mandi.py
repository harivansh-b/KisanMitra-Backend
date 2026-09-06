#!/usr/bin/env python3
"""
Seed Maharashtra APMC Mandi data.

DATA DISCLAIMER
===============
This script seeds DEMO mandi (market) data with REALISTIC price ranges
based on historical Maharashtra agricultural market patterns.

This is NOT live official data. For current official prices visit:
  - AGMARKNET: https://agmarknet.gov.in/
  - eNAM: https://www.enam.gov.in/

All seeded prices have source='AGMARKNET-DEMO' to clearly identify them
as demonstration data.

Usage:
    cd backend
    python scripts/seed_maharashtra_mandi.py

Safe to run multiple times (idempotent).
"""

import os
import sys
import uuid
import random
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./kisanmitra.db")

# ---------------------------------------------------------------------------
# Real Maharashtra APMC mandis
# (name, market_code, district, taluk, lat, lon)
# ---------------------------------------------------------------------------
MANDIS = [
    ("Pune APMC (Gultekdi)", "MH-PUN-001", "Pune", "Pune City", 18.4969, 73.8497),
    ("Nashik APMC", "MH-NAS-001", "Nashik", "Nashik", 19.9975, 73.7898),
    ("Lasalgaon", "MH-NAS-002", "Nashik", "Niphad", 20.1271, 74.0652),
    ("Niphad", "MH-NAS-003", "Nashik", "Niphad", 20.0721, 74.0898),
    ("Yeola", "MH-NAS-004", "Nashik", "Yeola", 20.0350, 74.4887),
    ("Malegaon APMC", "MH-NAS-005", "Nashik", "Malegaon", 20.5594, 74.5287),
    ("Nagpur APMC", "MH-NAG-001", "Nagpur", "Nagpur", 21.1458, 79.0882),
    ("Akola APMC", "MH-AKO-001", "Akola", "Akola", 20.7067, 77.0030),
    ("Amravati APMC", "MH-AMR-001", "Amravati", "Amravati", 20.9320, 77.7523),
    ("Sangli APMC", "MH-SAN-001", "Sangli", "Sangli-Miraj", 16.8524, 74.5648),
    ("Kolhapur APMC", "MH-KOL-001", "Kolhapur", "Kolhapur", 16.7050, 74.2433),
    ("Solapur APMC", "MH-SOL-001", "Solapur", "Solapur North", 17.6599, 75.9064),
    ("Jalgaon APMC", "MH-JAL-001", "Jalgaon", "Jalgaon", 21.0077, 75.5626),
    ("Satara APMC", "MH-SAT-001", "Satara", "Satara", 17.6805, 74.0183),
    ("Latur APMC", "MH-LAT-001", "Latur", "Latur", 18.4088, 76.5604),
    ("Nanded APMC", "MH-NAN-001", "Nanded", "Nanded", 19.1383, 77.3210),
    ("Dhule APMC", "MH-DHU-001", "Dhule", "Dhule", 20.9042, 74.7748),
    ("Ahmednagar APMC", "MH-AHM-001", "Ahmednagar", "Ahmednagar", 19.0952, 74.7497),
    ("Aurangabad APMC", "MH-AUR-001", "Chhatrapati Sambhajinagar", "Aurangabad", 19.8762, 75.3433),
    ("Chandrapur APMC", "MH-CHA-001", "Chandrapur", "Chandrapur", 19.9615, 79.2961),
    ("Wardha APMC", "MH-WAR-001", "Wardha", "Wardha", 20.7453, 78.6022),
    ("Yavatmal APMC", "MH-YAV-001", "Yavatmal", "Yavatmal", 20.3888, 78.1204),
    ("Buldhana APMC", "MH-BUL-001", "Buldhana", "Buldhana", 20.5292, 76.1833),
    ("Osmanabad APMC", "MH-OSM-001", "Dharashiv", "Osmanabad", 18.1860, 76.0367),
    ("Beed APMC", "MH-BEE-001", "Beed", "Beed", 18.9890, 75.7601),
    ("Parbhani APMC", "MH-PAR-001", "Parbhani", "Parbhani", 19.2741, 76.7747),
    ("Hingoli APMC", "MH-HIN-001", "Hingoli", "Hingoli", 19.7160, 77.1500),
    ("Washim APMC", "MH-WAS-001", "Washim", "Washim", 20.1067, 77.1444),
    ("Ratnagiri APMC", "MH-RAT-001", "Ratnagiri", "Ratnagiri", 16.9902, 73.3120),
    ("Sindhudurg (Oros)", "MH-SIN-001", "Sindhudurg", "Kudal", 16.0460, 73.6781),
    ("Thane Bhiwandi APMC", "MH-THA-001", "Thane", "Bhiwandi", 19.2813, 73.0491),
]

# (commodity_name, variety, grade, min_range, max_range, modal_base)
COMMODITY_PROFILES = [
    ("Onion", "Nashik Red", "Medium", 600, 3500, 1800),
    ("Onion", "Local", "Small", 400, 2000, 1000),
    ("Tomato", "Hybrid Red", "Grade A", 300, 4000, 1500),
    ("Potato", "Kufri Jyoti", "Grade A", 800, 2500, 1400),
    ("Grape", "Thompson Seedless", "Export", 2500, 10000, 5000),
    ("Pomegranate", "Bhagwa", "Grade A", 5000, 15000, 8000),
    ("Wheat", "Lokwan", "FAQ", 2015, 2800, 2300),
    ("Maize", "Yellow Hybrid", "FAQ", 1500, 2200, 1800),
    ("Soybean", "JS 335", "FAQ", 3800, 5800, 4600),
    ("Cotton", "Bt Cotton", "Fine", 5500, 9500, 7200),
    ("Turmeric", "Sangli", "Finger", 8000, 20000, 12000),
    ("Sugarcane", "CO-86032", "Generic", 280, 450, 350),
]

# Which commodities trade at which districts
DISTRICT_COMMODITIES = {
    "Nashik": ["Onion", "Tomato", "Grape", "Pomegranate", "Wheat"],
    "Pune": ["Onion", "Tomato", "Potato", "Wheat", "Soybean"],
    "Sangli": ["Turmeric", "Grape", "Sugarcane", "Onion", "Soybean"],
    "Kolhapur": ["Sugarcane", "Soybean", "Onion", "Tomato", "Potato"],
    "Satara": ["Sugarcane", "Soybean", "Onion", "Tomato"],
    "Nagpur": ["Wheat", "Soybean", "Cotton", "Tomato"],
    "Akola": ["Cotton", "Soybean", "Wheat", "Turmeric"],
    "Amravati": ["Cotton", "Soybean", "Wheat"],
    "Yavatmal": ["Cotton", "Soybean", "Wheat"],
    "Wardha": ["Cotton", "Soybean", "Wheat"],
    "Buldhana": ["Cotton", "Soybean", "Wheat"],
    "Washim": ["Cotton", "Soybean", "Wheat"],
    "Jalgaon": ["Cotton", "Soybean", "Wheat", "Maize"],
    "Solapur": ["Soybean", "Onion", "Wheat", "Sugarcane"],
    "Latur": ["Soybean", "Turmeric", "Wheat", "Cotton"],
    "Nanded": ["Soybean", "Turmeric", "Cotton", "Wheat"],
    "Parbhani": ["Soybean", "Cotton", "Wheat"],
    "Hingoli": ["Soybean", "Turmeric", "Wheat"],
    "Beed": ["Onion", "Soybean", "Cotton"],
    "Dharashiv": ["Onion", "Soybean", "Cotton"],
    "Ahmednagar": ["Onion", "Soybean", "Sugarcane", "Wheat"],
    "Chhatrapati Sambhajinagar": ["Soybean", "Cotton", "Onion", "Wheat"],
    "Dhule": ["Wheat", "Soybean", "Maize"],
    "Chandrapur": ["Cotton", "Soybean", "Wheat", "Maize"],
    "Ratnagiri": ["Wheat", "Potato"],
    "Sindhudurg": ["Wheat", "Potato"],
    "Thane": ["Tomato", "Onion", "Wheat", "Potato"],
}


def build_price_rows(mandi_id, district, rng):
    """Build a list of price row dicts for all commodities at this mandi."""
    rows = []
    today = date.today()
    days = [today - timedelta(days=i) for i in range(7)]
    allowed = DISTRICT_COMMODITIES.get(district, ["Wheat", "Onion", "Soybean"])

    for cn, variety, grade, min_range, max_range, modal_base in COMMODITY_PROFILES:
        if not any(c.lower() in cn.lower() for c in allowed):
            continue
        for arrival_date in days:
            fluctuation = rng.uniform(-0.08, 0.08)
            modal = round(modal_base * (1 + fluctuation))
            mn = round(modal * rng.uniform(0.82, 0.95))
            mx = round(modal * rng.uniform(1.05, 1.22))
            mn = min(mn, modal)
            mx = max(mx, modal)
            rows.append({
                "id": str(uuid.uuid4()),
                "mandi_id": mandi_id,
                "commodity_name": cn,
                "variety": variety,
                "grade": grade,
                "arrival_date": str(arrival_date),
                "arrival_quantity": round(rng.uniform(20, 500)),
                "min_price": mn,
                "max_price": mx,
                "modal_price": modal,
            })
    return rows


def main():
    print("=" * 60)
    print("KisanMitra - Maharashtra Mandi Seed")
    print("DATA: DEMO data with realistic price ranges.")
    print("NOT live official prices from AGMARKNET/eNAM.")
    print("=" * 60)

    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    is_pg = engine.dialect.name == "postgresql"
    rng = random.Random(42)

    with engine.connect() as conn:
        if is_pg:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
            conn.commit()

        # ---- Step 1: Upsert mandis ----
        print("\n-> Upserting mandis...")
        mandi_id_map = {}  # market_code -> mandi_id

        for name, market_code, district, taluk, lat, lon in MANDIS:
            existing = conn.execute(
                text("SELECT id FROM mandis WHERE market_code = :code"),
                {"code": market_code},
            ).fetchone()

            if existing:
                mandi_id_map[market_code] = existing[0]
                print(f"   skip (exists): {name}")
            else:
                mandi_id = str(uuid.uuid4())
                if is_pg:
                    conn.execute(
                        text("""
                            INSERT INTO mandis
                                (id, name, market_code, state, district, taluk,
                                 latitude, longitude, location, is_active, source)
                            VALUES
                                (:id, :name, :code, 'Maharashtra', :district, :taluk,
                                 :lat, :lon, ST_GeogFromText(:loc), TRUE, 'AGMARKNET-DEMO')
                        """),
                        {
                            "id": mandi_id, "name": name, "code": market_code,
                            "district": district, "taluk": taluk,
                            "lat": lat, "lon": lon,
                            "loc": f"SRID=4326;POINT({lon} {lat})",
                        },
                    )
                else:
                    conn.execute(
                        text("""
                            INSERT INTO mandis
                                (id, name, market_code, state, district, taluk,
                                 latitude, longitude, is_active, source)
                            VALUES
                                (:id, :name, :code, 'Maharashtra', :district, :taluk,
                                 :lat, :lon, 1, 'AGMARKNET-DEMO')
                        """),
                        {
                            "id": mandi_id, "name": name, "code": market_code,
                            "district": district, "taluk": taluk, "lat": lat, "lon": lon,
                        },
                    )
                mandi_id_map[market_code] = mandi_id
                print(f"   inserted: {name}")

        conn.commit()

        # ---- Step 2: Bulk-insert price rows ----
        print("\n-> Building price rows...")
        all_price_rows = []
        for name, market_code, district, taluk, lat, lon in MANDIS:
            mandi_id = mandi_id_map[market_code]
            rows = build_price_rows(mandi_id, district, rng)
            all_price_rows.extend(rows)

        print(f"   {len(all_price_rows)} total price rows to insert (skipping duplicates)...")

        if is_pg:
            # Postgres: INSERT ... ON CONFLICT DO NOTHING — one statement per row but committed in one batch
            inserted = 0
            BATCH = 200
            for i in range(0, len(all_price_rows), BATCH):
                batch = all_price_rows[i:i + BATCH]
                for r in batch:
                    conn.execute(
                        text("""
                            INSERT INTO mandi_prices
                                (id, mandi_id, commodity_name, variety, grade,
                                 arrival_date, arrival_quantity, arrival_unit,
                                 min_price, max_price, modal_price, price_unit, source)
                            VALUES
                                (:id, :mid, :cn, :var, :grd,
                                 :dt, :qty, 'Quintal',
                                 :mnp, :mxp, :mdp, 'INR/Quintal', 'AGMARKNET-DEMO')
                            ON CONFLICT ON CONSTRAINT uq_mandi_price_record DO NOTHING
                        """),
                        {
                            "id": r["id"], "mid": r["mandi_id"],
                            "cn": r["commodity_name"], "var": r["variety"],
                            "grd": r["grade"], "dt": r["arrival_date"],
                            "qty": r["arrival_quantity"],
                            "mnp": r["min_price"], "mxp": r["max_price"], "mdp": r["modal_price"],
                        },
                    )
                    inserted += 1
                conn.commit()
                print(f"   batch {i // BATCH + 1}: committed {min(i + BATCH, len(all_price_rows))}/{len(all_price_rows)}")
        else:
            # SQLite fallback
            inserted = 0
            for r in all_price_rows:
                existing = conn.execute(
                    text("""
                        SELECT id FROM mandi_prices
                        WHERE mandi_id=:mid AND commodity_name=:cn
                          AND variety=:var AND grade=:grd
                          AND arrival_date=:dt AND source='AGMARKNET-DEMO'
                    """),
                    {"mid": r["mandi_id"], "cn": r["commodity_name"],
                     "var": r["variety"], "grd": r["grade"], "dt": r["arrival_date"]},
                ).fetchone()
                if not existing:
                    conn.execute(
                        text("""
                            INSERT INTO mandi_prices
                                (id, mandi_id, commodity_name, variety, grade,
                                 arrival_date, arrival_quantity, arrival_unit,
                                 min_price, max_price, modal_price, price_unit, source)
                            VALUES
                                (:id, :mid, :cn, :var, :grd,
                                 :dt, :qty, 'Quintal',
                                 :mnp, :mxp, :mdp, 'INR/Quintal', 'AGMARKNET-DEMO')
                        """),
                        {
                            "id": r["id"], "mid": r["mandi_id"],
                            "cn": r["commodity_name"], "var": r["variety"],
                            "grd": r["grade"], "dt": r["arrival_date"],
                            "qty": r["arrival_quantity"],
                            "mnp": r["min_price"], "mxp": r["max_price"], "mdp": r["modal_price"],
                        },
                    )
                    inserted += 1
            conn.commit()

    print(f"\n[OK] Mandis seeded/verified: {len(MANDIS)}")
    print(f"[OK] Price rows attempted: {len(all_price_rows)}")
    print("\nDISCLAIMER: All prices labelled source='AGMARKNET-DEMO'")
    print("For live prices: https://agmarknet.gov.in/")
    print("=" * 60)


if __name__ == "__main__":
    main()
