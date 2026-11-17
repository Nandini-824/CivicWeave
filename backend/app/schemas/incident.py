from datetime import datetime
from pydantic import BaseModel


class IncidentResponse(BaseModel):
    id: str
    incident_number: str
    title: str
    description: str
    category: str
    center_latitude: float
    center_longitude: float
    first_reported_at: datetime
    last_reported_at: datetime
    recommended_priority: str
    approved_priority: str | None
    status: str
    department_name: str | None = None
    complaint_count: int = 0
    support_count: int = 0
    unique_reporters: int = 0

    class Config:
        from_attributes = True


class PriorityUpdate(BaseModel):
    approved_priority: str
    reason: str | None = None


class IncidentStatusUpdate(BaseModel):
    status: str
    remarks: str | None = None
    resolution_remarks: str | None = None
