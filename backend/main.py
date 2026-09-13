import pathsetup
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")   

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import contact, listings, search

app = FastAPI(title="Goose Nest API")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
def health():
    return {"ok": True}

app.include_router(listings.router)
app.include_router(search.router)
app.include_router(contact.router)
