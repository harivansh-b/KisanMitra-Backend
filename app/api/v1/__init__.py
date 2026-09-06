from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.farmers import router as farmers_router
from app.api.v1.fpos import router as fpos_router
from app.api.v1.buyers import router as buyers_router
from app.api.v1.crops import router as crops_router
from app.api.v1.listings import router as listings_router
from app.api.v1.requirements import router as requirements_router
from app.api.v1.marketplace import router as marketplace_router
from app.api.v1.orders import router as orders_router
from app.api.v1.transactions import router as transactions_router
from app.api.v1.storage import router as storage_router
from app.api.v1.mandi import market_router, router as mandi_router
from app.api.v1.directory import router as directory_router

api_v1_router = APIRouter()

api_v1_router.include_router(auth_router)
api_v1_router.include_router(farmers_router)
api_v1_router.include_router(fpos_router)
api_v1_router.include_router(buyers_router)
api_v1_router.include_router(crops_router)
api_v1_router.include_router(listings_router)
api_v1_router.include_router(requirements_router)
api_v1_router.include_router(marketplace_router)
api_v1_router.include_router(orders_router)
api_v1_router.include_router(transactions_router)
api_v1_router.include_router(storage_router)
api_v1_router.include_router(mandi_router)
api_v1_router.include_router(market_router)
api_v1_router.include_router(directory_router)
