import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./kisanmitra.db")

def fix_roles():
    print(f"Connecting to database: {DATABASE_URL}")
    engine = create_engine(DATABASE_URL)
    is_pg = "postgresql" in DATABASE_URL
    
    if is_pg:
        print("PostgreSQL detected. Altering enum userrole with AUTOCOMMIT...")
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            for new_val in ['STORAGE', 'TRANSPORT', 'QUALITY']:
                try:
                    conn.execute(text(f"ALTER TYPE userrole ADD VALUE IF NOT EXISTS '{new_val}';"))
                    print(f"Added '{new_val}' to enum userrole.")
                except Exception as e:
                    print(f"Notice adding '{new_val}': {e}")
    
    with engine.begin() as conn:
        print("Updating userrole in users table based on organization profiles...")
        
        # Storage Managers
        res_storage = conn.execute(text("""
            UPDATE users SET role = 'STORAGE'
            WHERE id IN (
                SELECT user_id FROM buyer_profiles 
                WHERE LOWER(organization_name) LIKE '%storage%' 
                   OR LOWER(organization_name) LIKE '%warehouse%' 
                   OR LOWER(organization_name) LIKE '%cold chain%'
            )
        """))
        print(f"Updated {res_storage.rowcount} users to STORAGE role.")

        # Transport Logistics
        res_transport = conn.execute(text("""
            UPDATE users SET role = 'TRANSPORT'
            WHERE id IN (
                SELECT user_id FROM buyer_profiles 
                WHERE LOWER(organization_name) LIKE '%transport%' 
                   OR LOWER(organization_name) LIKE '%logistics%' 
                   OR LOWER(organization_name) LIKE '%freight%' 
                   OR LOWER(organization_name) LIKE '%fleet%'
            )
        """))
        print(f"Updated {res_transport.rowcount} users to TRANSPORT role.")

        # Quality Assessors
        res_quality = conn.execute(text("""
            UPDATE users SET role = 'QUALITY'
            WHERE id IN (
                SELECT user_id FROM buyer_profiles 
                WHERE LOWER(organization_name) LIKE '%quality%' 
                   OR LOWER(organization_name) LIKE '%assessor%' 
                   OR LOWER(organization_name) LIKE '%cert%' 
                   OR LOWER(organization_name) LIKE '%testing%'
            )
        """))
        print(f"Updated {res_quality.rowcount} users to QUALITY role.")

    print("Database role column update completed successfully!")

if __name__ == "__main__":
    fix_roles()
