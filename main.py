import os
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from database import db, create_document, get_documents
from schemas import Drumkit, Collaborator

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Drumkits API ready"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = os.getenv("DATABASE_NAME") or "❌ Not Set"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    return response

# Simple username validation endpoint (simulate lookup in users collection)
@app.get("/validate-username")
def validate_username(username: str = Query(..., min_length=3, max_length=32)):
    # In real app you'd check users collection; here we assume any non-empty username is valid
    # If there is a users collection, we could query it. For now return ok.
    return {"username": username, "exists": True}

# Create Drumkit endpoint
class DrumkitCreate(BaseModel):
    # Archivos: we will receive URLs/paths already uploaded (file upload UI will be client-only in this MVP)
    archive_url: Optional[str] = None
    preview_urls: List[str] = Field(default_factory=list)
    cover_url: Optional[str] = None

    title: str = Field(..., max_length=60)
    release_at: str  # ISO string from client; will be parsed and validated server-side
    description: Optional[str] = Field(None, max_length=500)
    visibility: str = Field(..., pattern="^(privado|publico|no_listado)$")

    tags: List[str] = Field(default_factory=list)
    sounds_count: int = Field(..., ge=0, le=999)

    price_original: float = Field(..., ge=1.0, le=1000.0)
    is_free: bool = False
    offer_fixed: Optional[float] = Field(None, ge=0.0)
    offer_percent: Optional[int] = Field(None, ge=0, le=90)

    owner_username: str = Field(..., max_length=32)
    collaborators: List[Collaborator] = Field(default_factory=list)

class DrumkitResponse(BaseModel):
    id: str

@app.post("/drumkits", response_model=DrumkitResponse)
def create_drumkit(payload: DrumkitCreate):
    # Validate constraints not covered by schema
    # Tags: max 3 and each <= 15 chars
    if len(payload.tags) > 3 or any(len(t) > 15 for t in payload.tags):
        raise HTTPException(status_code=400, detail="Tags inválidos (max 3, cada uno max 15 caracteres)")

    # Pricing logic
    if payload.is_free:
        final_price = 0.0
        offer_fixed = None
        offer_percent = None
    else:
        offer_fixed = payload.offer_fixed
        offer_percent = payload.offer_percent
        if offer_fixed is not None and offer_fixed >= payload.price_original:
            raise HTTPException(status_code=400, detail="La oferta fija no puede ser mayor o igual al precio original")
        if offer_percent is not None and offer_percent > 90:
            raise HTTPException(status_code=400, detail="El porcentaje de oferta no puede ser mayor a 90%")
        # Calculate final price
        final_price = payload.price_original
        if offer_fixed is not None:
            final_price = payload.price_original - offer_fixed
        elif offer_percent is not None:
            final_price = payload.price_original * (1 - offer_percent/100)
        final_price = max(final_price, 0.0)

    # Release date validation: must be now at same minute or future within same minute rule
    try:
        client_dt = datetime.fromisoformat(payload.release_at.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        # If user specified a time earlier than now (minute precision), raise error
        if client_dt.replace(second=0, microsecond=0) < now.replace(second=0, microsecond=0):
            raise HTTPException(status_code=400, detail="La hora de lanzamiento ya pasó. Configura otra hora.")
    except ValueError:
        raise HTTPException(status_code=400, detail="Fecha de lanzamiento inválida")

    drumkit_doc = Drumkit(
        archive_url=payload.archive_url,
        preview_urls=payload.preview_urls,
        cover_url=payload.cover_url,
        title=payload.title,
        release_at=client_dt,
        description=payload.description,
        visibility=payload.visibility,  # type: ignore
        tags=payload.tags,
        sounds_count=payload.sounds_count,
        price_original=payload.price_original,
        is_free=payload.is_free,
        offer_fixed=offer_fixed,
        offer_percent=offer_percent,
        price_final=final_price,
        owner_username=payload.owner_username,
        collaborators=payload.collaborators,
    )

    new_id = create_document("drumkit", drumkit_doc)
    return {"id": new_id}
