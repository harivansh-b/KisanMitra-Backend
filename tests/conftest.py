import os
import sys
import pytest

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base, get_db
from app.core.security import create_test_jwt
from app.main import app
from app.models.crop import Crop
from app.models.user import User
from app.models.farmer import FarmerProfile
from app.models.fpo import FPOProfile
from app.models.buyer import BuyerProfile
from app.utils.enums import BuyerType, UnitEnum, UserRole, VerificationStatus

TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    os.environ["TESTING"] = "1"  # Used by storage_service to skip real Supabase upload
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
    os.environ.pop("TESTING", None)



@pytest.fixture
def db():
    session = TestingSessionLocal()
    yield session
    session.close()
    # Clean tables between tests
    with test_engine.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
        conn.commit()


@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def sample_crop(db):
    crop = db.query(Crop).filter(Crop.name == "Wheat").first()
    if not crop:
        crop = Crop(
            name="Wheat",
            local_name="Gehun",
            category="CEREALS",
            variety="Sharbati",
            default_unit=UnitEnum.QUINTAL,
            is_active=True,
        )
        db.add(crop)
        db.commit()
        db.refresh(crop)
    return crop


@pytest.fixture
def farmer_user(db):
    user = User(
        auth_user_id="farmer-auth-123",
        role=UserRole.FARMER,
        email="farmer@example.com",
        phone="9876543210",
        is_active=True,
    )
    db.add(user)
    db.flush()

    farmer = FarmerProfile(
        user_id=user.id,
        name="Ramesh Kumar",
        phone="9876543210",
        address="Farm Road 1",
        village="Khed",
        district="Pune",
        state="Maharashtra",
        pincode="410501",
        latitude=18.5204,
        longitude=73.8567,
        farm_size=5.5,
        preferred_crops=["Wheat", "Tomato"],
        verification_status=VerificationStatus.VERIFIED,
    )
    db.add(farmer)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def farmer_headers(farmer_user):
    token = create_test_jwt(auth_user_id=farmer_user.auth_user_id, email=farmer_user.email)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def fpo_user(db):
    user = User(
        auth_user_id="fpo-auth-456",
        role=UserRole.FPO,
        email="fpo@example.com",
        phone="9876543211",
        is_active=True,
    )
    db.add(user)
    db.flush()

    fpo = FPOProfile(
        user_id=user.id,
        organization_name="Sahyadri Farmers Producer Co",
        registration_number="FPO-MH-2023-001",
        contact_person="Vikas Patil",
        phone="9876543211",
        email="fpo@example.com",
        address="MIDC Agro Hub",
        village_or_city="Nashik",
        district="Nashik",
        state="Maharashtra",
        pincode="422001",
        latitude=19.9975,
        longitude=73.7898,
        description="Farmer Producer Company with 200+ members",
        verification_status=VerificationStatus.VERIFIED,
    )
    db.add(fpo)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def fpo_headers(fpo_user):
    token = create_test_jwt(auth_user_id=fpo_user.auth_user_id, email=fpo_user.email)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def buyer_user(db):
    user = User(
        auth_user_id="buyer-auth-789",
        role=UserRole.BUYER,
        email="buyer@example.com",
        phone="9876543212",
        is_active=True,
    )
    db.add(user)
    db.flush()

    buyer = BuyerProfile(
        user_id=user.id,
        organization_name="AgroFresh Wholesale Pvt Ltd",
        buyer_type=BuyerType.WHOLESALER,
        contact_person="Anil Sharma",
        phone="9876543212",
        email="buyer@example.com",
        address="APMC Market Yard",
        location_name="Navi Mumbai",
        latitude=19.0330,
        longitude=73.0297,
        business_description="Wholesale grain and vegetable distributor",
        verification_status=VerificationStatus.VERIFIED,
    )
    db.add(buyer)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def buyer_headers(buyer_user):
    token = create_test_jwt(auth_user_id=buyer_user.auth_user_id, email=buyer_user.email)
    return {"Authorization": f"Bearer {token}"}
