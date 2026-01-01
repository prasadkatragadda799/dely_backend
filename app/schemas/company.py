from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class CompanyBase(BaseModel):
    name: str
    logo: Optional[str] = None
    description: Optional[str] = None


class CompanyCreate(CompanyBase):
    pass


class CompanyResponse(BaseModel):
    id: UUID
    name: str
    logo: Optional[str]
    description: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class BrandResponse(BaseModel):
    name: str
    count: int

