from datetime import datetime

from pydantic import BaseModel, Field


class ComplaintCreate(BaseModel):
    title: str = Field(..., min_length=5, max_length=255)
    description: str = Field(..., min_length=10)

    category: str | None = None

    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)

    address: str = Field(..., min_length=3)
    city: str = Field(..., min_length=2)

    image_url: str | None = None

    # MongoDB ObjectId represented as string in the API
    link_to_incident_id: str | None = None

    submit_separately: bool = False


class AnalyzeComplaintRequest(BaseModel):
    title: str = Field(..., min_length=5)
    description: str = Field(..., min_length=10)

    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)

    category: str | None = None


class ComplaintResponse(BaseModel):
    # MongoDB ObjectId → string
    id: str

    complaint_number: str

    title: str
    description: str
    category: str

    latitude: float
    longitude: float

    address: str
    city: str

    image_url: str | None = None

    status: str

    suggested_department: str | None = None
    assigned_department: str | None = None

    created_at: datetime
    updated_at: datetime

    # MongoDB ObjectId → string
    related_incident_id: str | None = None
    related_incident_number: str | None = None


class StatusUpdate(BaseModel):
    status: str
    remarks: str | None = None


class FeedbackCreate(BaseModel):
    is_resolved: bool
    remarks: str | None = None