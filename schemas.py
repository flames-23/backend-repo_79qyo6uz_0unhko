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

from pydantic import BaseModel, Field
from typing import Optional, List

class Video(BaseModel):
    """
    Videos collection schema
    Collection name: "video" (lowercase of class name)
    """
    title: str = Field(..., description="Video title")
    description: Optional[str] = Field(None, description="Video description")
    filename: str = Field(..., description="Stored filename on server")
    content_type: str = Field(..., description="MIME type of uploaded file")
    size: int = Field(..., ge=0, description="Size in bytes")
    views: int = Field(0, ge=0, description="View count")
    tags: Optional[List[str]] = Field(default_factory=list, description="Tags for search")
