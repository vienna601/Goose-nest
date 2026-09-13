from fastapi import APIRouter
from schema import SearchRequirements, ScoredListing
from services.ranking import search as run_search
from services.enrich import enrich
from sample_data import SAMPLE_LISTINGS

router = APIRouter()

def _load_listings():
    # TEMP: sample data enriched on the fly. Swap to Supabase when the key is set.
    return [l.model_copy(update=enrich(l.lat, l.lng)) for l in SAMPLE_LISTINGS]

@router.post("/search", response_model=list[ScoredListing])
def search_listings(req: SearchRequirements):
    return run_search(_load_listings(), req)