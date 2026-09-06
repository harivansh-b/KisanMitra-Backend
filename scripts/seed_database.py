#!/usr/bin/env python3
"""
KisanMitra - Master Database Seed Script

Runs all seeders in the correct foreign-key dependency order:
  1. Alembic migrations (upgrade head)
  2. Crops (master data)
  3. Maharashtra mandis + price history
  4. Demo application entities (users, farmers, FPOs, buyers, listings, orders)

Safe to run multiple times (all sub-seeders are idempotent).

Usage:
    cd backend
    python scripts/seed_database.py
"""

import os
import subprocess
import sys
from pathlib import Path

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

SCRIPTS_DIR = Path(__file__).parent
BACKEND_DIR = SCRIPTS_DIR.parent


def run_step(label: str, fn):
    print(f"\n{'=' * 60}")
    print(f"  STEP: {label}")
    print(f"{'=' * 60}")
    try:
        fn()
        print(f"  [OK] {label} completed.")
    except Exception as exc:
        print(f"  [FAIL] {label} FAILED: {exc}")
        raise


def step_alembic():
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(BACKEND_DIR),
        capture_output=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Alembic upgrade failed (exit code {result.returncode})")


def step_crops():
    """Trigger crop seeding via the crop service (same as on startup)."""
    from app.core.database import SessionLocal
    from app.services.crop_service import crop_service

    db = SessionLocal()
    try:
        n = crop_service.seed_default_crops(db)
        if n:
            print(f"  -> Seeded {n} default crops")
        else:
            print("  -> Crops already exist - skipped")
    finally:
        db.close()


def step_mandis():
    """Run Maharashtra mandi seed."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "seed_maharashtra_mandi",
        str(SCRIPTS_DIR / "seed_maharashtra_mandi.py"),
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.main()


def step_demo_data():
    """Run demo application data seed."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "seed_demo_data",
        str(SCRIPTS_DIR / "seed_demo_data.py"),
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.main()


def main():
    print("\n" + "=" * 60)
    print("  KisanMitra - Full Database Seed")
    print("=" * 60)

    run_step("1. Alembic migrations (upgrade head)", step_alembic)
    run_step("2. Crops (master data)", step_crops)
    run_step("3. Maharashtra Mandi data", step_mandis)
    run_step("4. Demo application entities", step_demo_data)

    print("\n" + "=" * 60)
    print("  [OK] All seed steps completed successfully.")
    print("  Backend ready: uvicorn app.main:app --reload")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
