from fastapi import APIRouter, Query
from schema import Listing
from services.enrich import enrich
from sample_data import SAMPLE_LISTINGS

router = APIRouter()

@router.get("/listings", response_model=list[Listing])
def list_listings(limit: int = Query(50, le=200), offset: int = 0):
    items = [l.model_copy(update=enrich(l.lat, l.lng)) for l in SAMPLE_LISTINGS]
    return items[offset:offset + limit]