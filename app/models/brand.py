from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime

class BrandBase(BaseModel):
    name: str
    website_url: Optional[str] = None
    industry: Optional[str] = None
    aliases: Optional[List[str]] = None

class BrandCreate(BrandBase):
    pass

class Brand(BrandBase):
    id: UUID
    created_at: datetime

    model_config = {
        "from_attributes": True
    }

# DONE - brand.py
