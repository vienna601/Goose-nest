from fastapi import APIRouter
from schema import SearchRequirements, ScoredListing
from services.ranking import search as run_search
from services.listings_store import load_listings

router = APIRouter()

@router.post("/search", response_model=list[ScoredListing])
def search_listings(req: SearchRequirements):
    return run_search(load_listings(), req)
