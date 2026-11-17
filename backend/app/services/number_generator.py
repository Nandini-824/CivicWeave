from sqlalchemy.orm import Session
from app.models.complaint import Complaint
from app.models.incident import Incident


def generate_complaint_number(db: Session) -> str:
    count = db.query(Complaint).count()
    return f"CW-{count + 1:06d}"


def generate_incident_number(db: Session) -> str:
    count = db.query(Incident).count()
    return f"INC-{count + 1:06d}"
