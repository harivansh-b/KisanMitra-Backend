from datetime import date

from app.models.mandi import Mandi
from app.models.mandi_price import MandiPrice


def _seed_mandi_price(db, sample_crop):
    mandi = Mandi(
        name="Nashik APMC",
        market_code="MH-NAS-TEST",
        state="Maharashtra",
        district="Nashik",
        taluk="Nashik",
        latitude=19.9975,
        longitude=73.7898,
        source="TEST",
    )
    db.add(mandi)
    db.flush()
    price = MandiPrice(
        mandi_id=mandi.id,
        commodity_id=sample_crop.id,
        commodity_name="Wheat",
        variety="Sharbati",
        grade="FAQ",
        arrival_date=date(2026, 9, 6),
        arrival_quantity=20,
        min_price=2200,
        modal_price=2400,
        max_price=2600,
        source="TEST",
    )
    db.add(price)
    db.commit()
    return mandi


def test_mandi_prices_can_be_filtered(client, db, sample_crop):
    mandi = _seed_mandi_price(db, sample_crop)

    markets = client.get("/api/v1/mandi/mandis?district=Nashik")
    assert markets.status_code == 200
    assert markets.json()["items"][0]["id"] == mandi.id

    canonical_markets = client.get("/api/v1/mandis?district=Nashik")
    assert canonical_markets.status_code == 200
    assert canonical_markets.json()["items"][0]["id"] == mandi.id

    prices = client.get("/api/v1/mandi/prices?commodity=Wheat&district=Nashik")
    assert prices.status_code == 200
    assert prices.json()["total"] == 1
    assert prices.json()["items"][0]["modal_price"] == 2400


def test_nearby_mandis_uses_geographic_query(client, db, sample_crop):
    mandi = _seed_mandi_price(db, sample_crop)

    response = client.get("/api/v1/mandi/nearby?latitude=19.99&longitude=73.79&radius_km=20")
    assert response.status_code == 200
    assert response.json()[0]["mandi"]["id"] == mandi.id
    assert response.json()[0]["distance_km"] < 2
