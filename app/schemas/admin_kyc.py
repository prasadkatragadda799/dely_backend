from pydantic import BaseModel
from typing import Optional


class KYCVerify(BaseModel):
    comments: Optional[str] = None


class KYCReject(BaseModel):
    reason: str

