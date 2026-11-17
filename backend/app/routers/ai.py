from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.models.user import User
from app.schemas.complaint import AnalyzeComplaintRequest
from app.security.auth import get_current_user

from app.ai.classifier import classify_complaint
from app.services.complaint_service import analyze_complaint_preview

from app.database import get_db


router = APIRouter(
    prefix="/api/ai",
    tags=["ai"]
)


class ClassifyRequest(BaseModel):
    title: str = Field(..., min_length=3)
    description: str = Field(..., min_length=5)


# ============================================================
# CLASSIFY COMPLAINT
# ============================================================

@router.post("/classify")
async def classify(
    data: ClassifyRequest,
    current_user: User = Depends(get_current_user),
):
    return classify_complaint(
        data.title,
        data.description
    )


# ============================================================
# ANALYZE COMPLAINT
# ============================================================

@router.post("/analyze-complaint")
async def analyze_complaint(
    data: AnalyzeComplaintRequest,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await analyze_complaint_preview(
        db,
        data.title,
        data.description,
        data.latitude,
        data.longitude,
        data.category,
    )

    return result


# ============================================================
# FIND RELATED INCIDENTS
# ============================================================

@router.post("/find-related")
async def find_related(
    data: AnalyzeComplaintRequest,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await analyze_complaint_preview(
        db,
        data.title,
        data.description,
        data.latitude,
        data.longitude,
        data.category,
    )

    return {
        "related_incidents": result.get(
            "related_incidents",
            []
        ),
        "potential_related_incidents": result.get(
            "potential_related_incidents",
            []
        ),
    }