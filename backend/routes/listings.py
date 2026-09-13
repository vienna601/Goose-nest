from fastapi import APIRouter, Query
from schema import Listing
from services.listings_store import load_listings, listings_source

router = APIRouter()

@router.get("/listings", response_model=list[Listing])
def list_listings(limit: int = Query(50, le=1000), offset: int = 0):
    items = load_listings()
    return items[offset:offset + limit]

@router.get("/listings/source")
def which_source():
    load_listings()
    return {"source": listings_source(), "count": len(load_listings())}
