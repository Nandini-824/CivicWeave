from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
)

from app.database import get_db
from app.models.user import User, UserRole
from app.models.complaint import ComplaintStatus
from app.schemas.complaint import (
    ComplaintCreate,
    ComplaintResponse,
    StatusUpdate,
    FeedbackCreate,
)
from app.security.auth import get_current_user, require_roles
from app.services.complaint_service import create_complaint
from app.services.status_service import record_status_change
from app.services.notification_service import create_notification
from app.config import get_settings

import cloudinary
import cloudinary.uploader


router = APIRouter(
    prefix="/api/complaints",
    tags=["complaints"],
)

settings = get_settings()


# ============================================================
# CONSTANTS
# ============================================================

ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
}

MAX_IMAGE_SIZE = 5 * 1024 * 1024


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _to_object_id(value: str):
    """
    Convert a string ID to MongoDB ObjectId.

    Returns None if the ID is invalid.
    """
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        return None


async def _find_complaint(db, complaint_id: str):
    """
    Find a complaint by its MongoDB ObjectId.
    """
    object_id = _to_object_id(complaint_id)

    if object_id is None:
        return None

    return await db.complaints.find_one({"_id": object_id})


async def _get_department_name(db, department_id):
    """
    Get department name.

    Supports both ObjectId and string department IDs because
    older/newer MongoDB documents may use either representation.
    """

    if department_id is None:
        return None

    # ObjectId representation
    if isinstance(department_id, ObjectId):
        department = await db.departments.find_one(
            {"_id": department_id}
        )

        if department:
            return department.get("name")

        return None

    # String representation
    department = await db.departments.find_one(
        {"_id": department_id}
    )

    if department:
        return department.get("name")

    # Try converting string to ObjectId
    object_id = _to_object_id(str(department_id))

    if object_id:
        department = await db.departments.find_one(
            {"_id": object_id}
        )

        if department:
            return department.get("name")

    return None


async def _complaint_to_response(db, complaint: dict) -> dict:
    """
    Convert MongoDB complaint document into ComplaintResponse format.
    """

    complaint_id = complaint.get("_id")

    # --------------------------------------------------------
    # Department names
    # --------------------------------------------------------

    suggested_department = await _get_department_name(
        db,
        complaint.get("suggested_department_id"),
    )

    assigned_department = await _get_department_name(
        db,
        complaint.get("assigned_department_id"),
    )

    # --------------------------------------------------------
    # Find related incident
    # --------------------------------------------------------

    incident_link = None

    if complaint_id is not None:
        incident_link = await db.incident_complaints.find_one(
            {
                "complaint_id": complaint_id
            }
        )

        # Backward compatibility if IDs were stored as strings
        if incident_link is None:
            incident_link = await db.incident_complaints.find_one(
                {
                    "complaint_id": str(complaint_id)
                }
            )

    incident_id = None
    incident_number = None

    if incident_link:
        incident_id_value = incident_link.get("incident_id")

        if incident_id_value is not None:

            # If stored as ObjectId
            if isinstance(incident_id_value, ObjectId):

                incident = await db.incidents.find_one(
                    {
                        "_id": incident_id_value
                    }
                )

            else:

                # Try string first
                incident = await db.incidents.find_one(
                    {
                        "_id": incident_id_value
                    }
                )

                # Try ObjectId
                if incident is None:
                    object_id = _to_object_id(
                        str(incident_id_value)
                    )

                    if object_id:
                        incident = await db.incidents.find_one(
                            {
                                "_id": object_id
                            }
                        )
                    else:
                        incident = None

            if incident:
                incident_id = str(incident["_id"])
                incident_number = incident.get("incident_number")

    # --------------------------------------------------------
    # Convert MongoDB document
    # --------------------------------------------------------

    created_at = complaint.get("created_at")
    updated_at = complaint.get("updated_at")

    response = {
        "id": str(complaint["_id"]),
        "complaint_number": complaint.get(
            "complaint_number",
            "",
        ),
        "title": complaint.get(
            "title",
            "",
        ),
        "description": complaint.get(
            "description",
            "",
        ),
        "category": complaint.get(
            "category",
            "",
        ),
        "latitude": complaint.get(
            "latitude",
            0.0,
        ),
        "longitude": complaint.get(
            "longitude",
            0.0,
        ),
        "address": complaint.get(
            "address",
            "",
        ),
        "city": complaint.get(
            "city",
            "",
        ),
        "image_url": complaint.get(
            "image_url"
        ),
        "status": complaint.get(
            "status",
            ComplaintStatus.submitted.value,
        ),
        "suggested_department": suggested_department,
        "assigned_department": assigned_department,
        "created_at": created_at,
        "updated_at": updated_at,
        "related_incident_id": incident_id,
        "related_incident_number": incident_number,
    }

    return response


# ============================================================
# CREATE COMPLAINT
# ============================================================

@router.post(
    "",
    response_model=ComplaintResponse,
)
async def submit_complaint(
    data: ComplaintCreate,
    db=Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.citizen)
    ),
):
    """
    Submit a new civic complaint.

    The complaint service handles:

    - Category prediction
    - Department suggestion
    - Semantic embedding
    - Incident matching
    - Incident creation/linking
    - Priority recommendation
    """

    complaint = await create_complaint(
        db=db,
        citizen_id=str(current_user.id),
        title=data.title,
        description=data.description,
        category=data.category,
        latitude=data.latitude,
        longitude=data.longitude,
        address=data.address,
        city=data.city,
        image_url=data.image_url,
        link_to_incident_id=data.link_to_incident_id,
        submit_separately=data.submit_separately,
    )

    # create_complaint may return either a Pydantic model
    # or a MongoDB dictionary depending on implementation.

    if hasattr(complaint, "model_dump"):
        complaint_document = complaint.model_dump()

        # If service returned its own ID
        if complaint_document.get("id"):
            object_id = _to_object_id(
                str(complaint_document["id"])
            )

            if object_id:
                complaint_document["_id"] = object_id

        # Try fetching the actual MongoDB document
        if complaint_document.get("_id"):
            saved_complaint = await db.complaints.find_one(
                {
                    "_id": complaint_document["_id"]
                }
            )

            if saved_complaint:
                complaint_document = saved_complaint

    else:
        complaint_document = complaint

    # If service returned only the inserted document
    if "_id" not in complaint_document:

        complaint_id = complaint_document.get("id")

        if complaint_id:
            object_id = _to_object_id(
                str(complaint_id)
            )

            if object_id:
                saved_complaint = await db.complaints.find_one(
                    {
                        "_id": object_id
                    }
                )

                if saved_complaint:
                    complaint_document = saved_complaint

    if "_id" not in complaint_document:
        raise HTTPException(
            status_code=500,
            detail="Complaint was created but could not be retrieved",
        )

    return await _complaint_to_response(
        db,
        complaint_document,
    )


# ============================================================
# IMAGE UPLOAD
# ============================================================

@router.post("/upload-image")
async def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    Upload complaint image.

    Currently uses Cloudinary when configured.
    If Cloudinary is not configured, the endpoint safely
    returns None instead of failing.
    """

    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid file type. "
                "Allowed: JPG, JPEG, PNG, WEBP"
            ),
        )

    contents = await file.read()

    if len(contents) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="File too large. Maximum 5MB",
        )

    # --------------------------------------------------------
    # Cloudinary
    # --------------------------------------------------------

    if settings.cloudinary_configured:

        cloudinary.config(
            cloud_name=settings.cloudinary_cloud_name,
            api_key=settings.cloudinary_api_key,
            api_secret=settings.cloudinary_api_secret,
        )

        result = cloudinary.uploader.upload(
            contents,
            folder="civicweave",
        )

        return {
            "image_url": result["secure_url"]
        }

    # --------------------------------------------------------
    # Cloudinary not configured
    # --------------------------------------------------------

    return {
        "image_url": None,
        "message": (
            "Cloudinary not configured. "
            "Proceed without image."
        ),
    }


# ============================================================
# MY COMPLAINTS
# ============================================================

@router.get(
    "/my",
    response_model=list[ComplaintResponse],
)
async def my_complaints(
    db=Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.citizen)
    ),
):
    """
    Get complaints submitted by the logged-in citizen.
    """

    cursor = db.complaints.find(
        {
            "citizen_id": str(current_user.id)
        }
    ).sort(
        "created_at",
        -1,
    )

    complaints = await cursor.to_list(
        length=None
    )

    return [
        await _complaint_to_response(
            db,
            complaint,
        )
        for complaint in complaints
    ]


# ============================================================
# GET SINGLE COMPLAINT
# ============================================================

@router.get(
    "/{complaint_id}",
    response_model=ComplaintResponse,
)
async def get_complaint(
    complaint_id: str,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a single complaint.

    Citizens can only view their own complaints.
    Officers/Admins can view complaints according to their role.
    """

    complaint = await _find_complaint(
        db,
        complaint_id,
    )

    if not complaint:
        raise HTTPException(
            status_code=404,
            detail="Complaint not found",
        )

    # Citizen ownership check
    if (
        current_user.role == UserRole.citizen
        and complaint.get("citizen_id")
        != str(current_user.id)
    ):
        raise HTTPException(
            status_code=403,
            detail="Access denied",
        )

    return await _complaint_to_response(
        db,
        complaint,
    )


# ============================================================
# COMPLAINT TIMELINE
# ============================================================

@router.get(
    "/{complaint_id}/timeline"
)
async def get_complaint_timeline(
    complaint_id: str,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get complaint status history.
    """

    complaint = await _find_complaint(
        db,
        complaint_id,
    )

    if not complaint:
        raise HTTPException(
            status_code=404,
            detail="Complaint not found",
        )

    # Citizen ownership check
    if (
        current_user.role == UserRole.citizen
        and complaint.get("citizen_id")
        != str(current_user.id)
    ):
        raise HTTPException(
            status_code=403,
            detail="Access denied",
        )

    complaint_object_id = complaint["_id"]

    # Search ObjectId representation
    history = await db.status_history.find(
        {
            "entity_type": "complaint",
            "entity_id": complaint_object_id,
        }
    ).sort(
        "created_at",
        1,
    ).to_list(
        length=None
    )

    # Backward compatibility for string IDs
    if not history:
        history = await db.status_history.find(
            {
                "entity_type": "complaint",
                "entity_id": str(complaint_object_id),
            }
        ).sort(
            "created_at",
            1,
        ).to_list(
            length=None
        )

    return [
        {
            "previous_status": item.get(
                "previous_status"
            ),
            "new_status": item.get(
                "new_status"
            ),
            "remarks": item.get(
                "remarks"
            ),
            "created_at": item.get(
                "created_at"
            ),
        }
        for item in history
    ]


# ============================================================
# LIST ALL COMPLAINTS
# ============================================================

@router.get("")
async def list_complaints(
    db=Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.admin,
            UserRole.officer,
        )
    ),
):
    """
    List complaints for officers/admins.

    Officers only see complaints belonging to
    their assigned department.
    """

    query = {}

    # --------------------------------------------------------
    # Officer department filtering
    # --------------------------------------------------------

    if current_user.role == UserRole.officer:

        officer_id = str(current_user.id)

        assignment = await db.officer_assignments.find_one(
            {
                "officer_id": officer_id
            }
        )

        if assignment:

            department_id = assignment.get(
                "department_id"
            )

            # Department ID may be stored as ObjectId
            # or string depending on migration state.

            query = {
                "$or": [
                    {
                        "assigned_department_id":
                            department_id
                    },
                    {
                        "assigned_department_id":
                            str(department_id)
                    },
                ]
            }

        else:
            # Officer has no department assignment.
            # Return an empty list rather than exposing
            # all complaints.
            return []

    # --------------------------------------------------------
    # Query complaints
    # --------------------------------------------------------

    complaints = await db.complaints.find(
        query
    ).sort(
        "created_at",
        -1,
    ).to_list(
        length=None
    )

    return [
        await _complaint_to_response(
            db,
            complaint,
        )
        for complaint in complaints
    ]


# ============================================================
# UPDATE COMPLAINT STATUS
# ============================================================

@router.patch(
    "/{complaint_id}/status"
)
async def update_complaint_status(
    complaint_id: str,
    data: StatusUpdate,
    db=Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.officer,
            UserRole.admin,
        )
    ),
):
    """
    Update complaint status.

    Also:
    - records status history
    - sends citizen notification
    """

    complaint = await _find_complaint(
        db,
        complaint_id,
    )

    if not complaint:
        raise HTTPException(
            status_code=404,
            detail="Complaint not found",
        )

    previous_status = complaint.get(
        "status"
    )

    # --------------------------------------------------------
    # Update complaint
    # --------------------------------------------------------

    now = datetime.now(timezone.utc)

    await db.complaints.update_one(
        {
            "_id": complaint["_id"]
        },
        {
            "$set": {
                "status": data.status,
                "updated_at": now,
            }
        },
    )

    # --------------------------------------------------------
    # Record status history
    # --------------------------------------------------------

    await record_status_change(
        db=db,
        entity_type="complaint",
        entity_id=str(complaint["_id"]),
        previous_status=previous_status,
        new_status=data.status,
        changed_by=str(current_user.id),
        remarks=data.remarks,
    )

    # --------------------------------------------------------
    # Notify citizen
    # --------------------------------------------------------

    citizen_id = complaint.get(
        "citizen_id"
    )

    if citizen_id:
        await create_notification(
            db=db,
            user_id=str(citizen_id),
            title="Complaint Status Updated",
            message=(
                f"Your complaint "
                f"{complaint.get('complaint_number', '')} "
                f"status changed to {data.status}"
            ),
        )

    # --------------------------------------------------------
    # Return updated complaint
    # --------------------------------------------------------

    updated_complaint = await db.complaints.find_one(
        {
            "_id": complaint["_id"]
        }
    )

    return await _complaint_to_response(
        db,
        updated_complaint,
    )


# ============================================================
# FEEDBACK HELPER
# ============================================================

async def _submit_feedback(
    complaint_id: str,
    data: FeedbackCreate,
    db,
    current_user: User,
):
    """
    Internal helper shared by:
    - /feedback
    - /reopen-request
    """

    complaint = await _find_complaint(
        db,
        complaint_id,
    )

    # --------------------------------------------------------
    # Validate complaint ownership
    # --------------------------------------------------------

    if (
        not complaint
        or complaint.get("citizen_id")
        != str(current_user.id)
    ):
        raise HTTPException(
            status_code=404,
            detail="Complaint not found",
        )

    # --------------------------------------------------------
    # Feedback allowed only after resolution
    # --------------------------------------------------------

    if complaint.get("status") not in (
        ComplaintStatus.resolved.value,
        ComplaintStatus.closed.value,
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Feedback only allowed "
                "after resolution"
            ),
        )

    # --------------------------------------------------------
    # Store feedback
    # --------------------------------------------------------

    feedback_document = {
        "complaint_id": complaint["_id"],
        "citizen_id": str(current_user.id),
        "is_resolved": data.is_resolved,
        "remarks": data.remarks,
        "created_at": datetime.now(timezone.utc),
    }

    await db.resolution_feedback.insert_one(
        feedback_document
    )

    # --------------------------------------------------------
    # If citizen says issue is unresolved
    # --------------------------------------------------------

    if not data.is_resolved:

        previous_status = complaint.get(
            "status"
        )

        now = datetime.now(timezone.utc)

        await db.complaints.update_one(
            {
                "_id": complaint["_id"]
            },
            {
                "$set": {
                    "status":
                        ComplaintStatus.reopened.value,
                    "updated_at": now,
                }
            },
        )

        # ----------------------------------------------------
        # Record status change
        # ----------------------------------------------------

        await record_status_change(
            db=db,
            entity_type="complaint",
            entity_id=str(complaint["_id"]),
            previous_status=previous_status,
            new_status=ComplaintStatus.reopened.value,
            changed_by=str(current_user.id),
            remarks=(
                data.remarks
                or "Citizen reported issue unresolved"
            ),
        )

        # ----------------------------------------------------
        # Notify assigned department officers
        # ----------------------------------------------------

        assigned_department_id = complaint.get(
            "assigned_department_id"
        )

        if assigned_department_id:

            officers = await db.officer_assignments.find(
                {
                    "$or": [
                        {
                            "department_id":
                                assigned_department_id
                        },
                        {
                            "department_id":
                                str(
                                    assigned_department_id
                                )
                        },
                    ]
                }
            ).to_list(
                length=None
            )

            for officer in officers:

                officer_id = officer.get(
                    "officer_id"
                )

                if officer_id:

                    await create_notification(
                        db=db,
                        user_id=str(officer_id),
                        title="Reopening Request",
                        message=(
                            f"Complaint "
                            f"{complaint.get('complaint_number', '')} "
                            f"was reopened by the citizen."
                        ),
                    )

    return {
        "message": "Feedback submitted",
        "is_resolved": data.is_resolved,
    }


# ============================================================
# SUBMIT FEEDBACK
# ============================================================

@router.post(
    "/{complaint_id}/feedback"
)
async def submit_feedback(
    complaint_id: str,
    data: FeedbackCreate,
    db=Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.citizen)
    ),
):
    """
    Submit resolution feedback.

    If citizen says the issue is unresolved,
    the complaint is reopened.
    """

    return await _submit_feedback(
        complaint_id=complaint_id,
        data=data,
        db=db,
        current_user=current_user,
    )


# ============================================================
# REOPEN REQUEST
# ============================================================

@router.post(
    "/{complaint_id}/reopen-request"
)
async def reopen_request(
    complaint_id: str,
    data: FeedbackCreate,
    db=Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.citizen)
    ),
):
    """
    Reopen an already resolved/closed complaint.

    Uses the same feedback workflow.
    """

    return await _submit_feedback(
        complaint_id=complaint_id,
        data=data,
        db=db,
        current_user=current_user,
    )