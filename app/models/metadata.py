"""
Pydantic models for data validation and serialization.
"""
from pydantic import BaseModel, Field, HttpUrl
from typing import Dict, List, Optional, Any
from datetime import datetime
from bson import ObjectId


class PyObjectId(ObjectId):
    """Custom ObjectId type for Pydantic."""
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)
    
    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema):
        field_schema.update(type="string")


class MetadataCreateRequest(BaseModel):
    """Request model for creating metadata."""
    url: HttpUrl = Field(..., description="URL to collect metadata from")
    
    class Config:
        json_schema_extra = {
            "example": {"url": "https://example.com"}
        }


class MetadataResponse(BaseModel):
    """Response model for metadata retrieval."""
    id: Optional[str] = Field(None, alias="_id")
    url: str
    headers: Dict[str, str]
    cookies: Dict[str, str]
    page_source: str
    status_code: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}


class MetadataPendingResponse(BaseModel):
    """Response model for pending metadata collection."""
    url: str
    status: str = "pending"
    message: str = "Metadata collection initiated. Please retry shortly."


class MetadataDocument(BaseModel):
    """Internal document model for MongoDB storage."""
    url: str
    headers: Dict[str, Any]
    cookies: Dict[str, str]
    page_source: str
    status_code: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True
