"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field, EmailStr, AwareDatetime
from typing import Optional, List, Literal

# Core schemas used by the app

class User(BaseModel):
    """
    Users collection schema
    Collection name: "user" (lowercase of class name)
    """
    username: str = Field(..., min_length=3, max_length=32, description="Unique username")
    email: EmailStr
    display_name: Optional[str] = Field(None, max_length=64)
    is_active: bool = Field(True)

class Collaborator(BaseModel):
    username: str = Field(..., max_length=32)
    role: Literal["productor", "Ingeniero de audio", "Artista"]
    share_percent: int = Field(..., ge=0, le=100, description="% de ventas")

class Drumkit(BaseModel):
    """
    Drumkits collection schema
    Collection name: "drumkit"
    """
    # Archivos
    archive_url: Optional[str] = Field(None, description="Ruta del .zip/.rar")
    preview_urls: List[str] = Field(default_factory=list, description="Lista de previews .mp3/.wav")
    cover_url: Optional[str] = Field(None, description="Portada 1080x1080+")

    # Info básica
    title: str = Field(..., max_length=60)
    release_at: AwareDatetime
    description: Optional[str] = Field(None, max_length=500)
    visibility: Literal["privado", "publico", "no_listado"]

    # Metadatos
    tags: List[str] = Field(default_factory=list, description="Max 3, cada uno <=15 chars")
    sounds_count: int = Field(..., ge=0, le=999)

    # Precios
    price_original: float = Field(..., ge=1.0, le=1000.0)
    is_free: bool = Field(False)
    offer_fixed: Optional[float] = Field(None, ge=0.0)
    offer_percent: Optional[int] = Field(None, ge=0, le=90)
    price_final: float = Field(..., ge=0.0)

    # Colaboraciones
    owner_username: str = Field(..., max_length=32)
    collaborators: List[Collaborator] = Field(default_factory=list)

# Example schemas kept for reference (not used by app directly)
class Product(BaseModel):
    title: str
    description: Optional[str] = None
    price: float
    category: str
    in_stock: bool = True
