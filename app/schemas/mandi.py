from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class MandiBase(BaseModel):
    name: str
    market_code: Optional[str] = None
    state: str = "Maharashtra"
    district: str
    taluk: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_active: bool = True
    source: Optional[str] = None


class MandiCreate(MandiBase):
    pass


class MandiResponse(MandiBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MandiPriceBase(BaseModel):
    mandi_id: str
    commodity_id: Optional[str] = None
    commodity_name: str
    variety: Optional[str] = None
    grade: Optional[str] = None
    arrival_date: date
    arrival_quantity: Optional[float] = None
    arrival_unit: Optional[str] = "Quintal"
    min_price: float = Field(..., ge=0)
    max_price: float = Field(..., ge=0)
    modal_price: float = Field(..., ge=0)
    price_unit: str = "INR/Quintal"
    source: str = "AGMARKNET"
    source_record_id: Optional[str] = None


class MandiPriceCreate(MandiPriceBase):
    pass


class MandiPriceResponse(MandiPriceBase):
    id: str
    fetched_at: datetime
    created_at: datetime
    updated_at: datetime
    mandi: Optional[MandiResponse] = None

    model_config = ConfigDict(from_attributes=True)


class MandiPriceFilter(BaseModel):
    mandi_id: Optional[str] = None
    district: Optional[str] = None
    commodity: Optional[str] = None
    variety: Optional[str] = None
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None


class NearbyMandiResult(BaseModel):
    mandi: MandiResponse
    distance_km: float

    model_config = ConfigDict(from_attributes=True)


class PredictionPoint(BaseModel):
    ds: str
    predicted_modal_price: float
    temp_max: float
    temp_min: float
    temp_mean: float
    rainfall: float
    et0: float


class ModelMetrics(BaseModel):
    mae: float
    rmse: float
    mape: float
    training_markets_count: int
    total_observations: int
    test_observations: int


class PricePredictionForecastResponse(BaseModel):
    unique_id: str
    market_name: str
    commodity: str = "Onion"
    district: str = "Nashik"
    model_type: str = "N-BEATSX (NeuralForecast)"
    input_window_days: int = 60
    forecast_horizon_days: int = 7
    weather_source: str = "Open-Meteo (Nashik Lat: 20.0059, Lon: 73.7897)"
    metrics: Optional[ModelMetrics] = None
    forecasts: List[PredictionPoint]


