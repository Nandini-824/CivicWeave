from datetime import datetime, timezone, timedelta

from bson import ObjectId
from bson.errors import InvalidId

from fastapi import APIRouter, Depends, HTTPException

from app.database import get_db
from app.models.user import User, UserRole
from app.models.incident import LinkStatus
from app.security.auth import require_roles
from app.services.complaint_service import (
    _recalculate_incident_priority,
)
from app.services.status_service import (
    record_status_change,
)
from app.routers.incidents import (
    _incident_to_response,
)
from app.routers.complaints import (
    _complaint_to_response,
)


router = APIRouter(
    prefix="/api/officer",
    tags=["officer"],
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _to_object_id(value):
    """
    Convert a value to MongoDB ObjectId.
    Returns None if invalid.
    """

    if isinstance(value, ObjectId):
        return value

    try:
        return ObjectId(str(value))
    except (InvalidId, TypeError):
        return None


async def _get_officer_department(
    db,
    officer_id,
):
    """
    Get the department assignment of an officer.
    """

    officer_id = str(officer_id)

    assignment = await db.officer_assignments.find_one(
        {
            "officer_id": officer_id
        }
    )

    if not assignment:
        raise HTTPException(
            status_code=403,
            detail="No department assignment found",
        )

    return assignment


async def _find_incident(
    db,
    incident_id,
):
    """
    Find an incident by MongoDB ObjectId.
    """

    object_id = _to_object_id(
        incident_id
    )

    if object_id is None:
        return None

    return await db.incidents.find_one(
        {
            "_id": object_id
        }
    )


async def _find_complaint(
    db,
    complaint_id,
):
    """
    Find a complaint using either ObjectId
    or string representation.
    """

    if isinstance(
        complaint_id,
        ObjectId,
    ):
        return await db.complaints.find_one(
            {
                "_id": complaint_id
            }
        )

    object_id = _to_object_id(
        complaint_id
    )

    if object_id:

        complaint = await db.complaints.find_one(
            {
                "_id": object_id
            }
        )

        if complaint:
            return complaint

    return await db.complaints.find_one(
        {
            "_id": complaint_id
        }
    )


async def _find_link(
    db,
    link_id,
):
    """
    Find an incident-complaint link.
    """

    object_id = _to_object_id(
        link_id
    )

    if object_id:

        link = await db.incident_complaints.find_one(
            {
                "_id": object_id
            }
        )

        if link:
            return link

    return await db.incident_complaints.find_one(
        {
            "_id": link_id
        }
    )


def _department_match(
    department_id,
):
    """
    Build a MongoDB condition that supports
    both ObjectId and string department IDs.
    """

    if isinstance(
        department_id,
        ObjectId,
    ):
        return {
            "$or": [
                {
                    "department_id":
                        department_id
                },
                {
                    "department_id":
                        str(department_id)
                },
            ]
        }

    object_id = _to_object_id(
        department_id
    )

    values = [
        department_id,
        str(department_id),
    ]

    if object_id:
        values.append(object_id)

    return {
        "department_id": {
            "$in": values
        }
    }


def _assigned_department_match(
    department_id,
):
    """
    Build a MongoDB condition for complaint
    assigned_department_id.
    """

    values = [
        department_id,
        str(department_id),
    ]

    object_id = _to_object_id(
        department_id
    )

    if object_id:
        values.append(object_id)

    return {
        "assigned_department_id": {
            "$in": values
        }
    }


# ============================================================
# OFFICER DASHBOARD
# ============================================================

@router.get("/dashboard")
async def officer_dashboard(
    db=Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.officer
        )
    ),
):
    """
    Officer dashboard statistics.

    Returns:
    - Total assigned complaints
    - Active incidents
    - High/Critical incidents
    - Resolved incidents
    - Overdue incidents
    """

    assignment = await _get_officer_department(
        db,
        current_user.id,
    )

    department_id = assignment.get(
        "department_id"
    )

    # --------------------------------------------------------
    # Total assigned complaints
    # --------------------------------------------------------

    total_complaints = (
        await db.complaints.count_documents(
            _assigned_department_match(
                department_id
            )
        )
    )

    # --------------------------------------------------------
    # Active incidents
    # --------------------------------------------------------

    active_query = {
        **_department_match(
            department_id
        ),
        "status": {
            "$nin": [
                "Resolved",
                "Closed",
            ]
        },
    }

    active_incidents = (
        await db.incidents.count_documents(
            active_query
        )
    )

    # --------------------------------------------------------
    # High priority incidents
    # --------------------------------------------------------

    high_priority_query = {
        **_department_match(
            department_id
        ),
        "$or": [
            {
                "approved_priority": {
                    "$in": [
                        "High",
                        "Critical",
                    ]
                }
            },
            {
                "recommended_priority": {
                    "$in": [
                        "High",
                        "Critical",
                    ]
                }
            },
        ],
    }

    high_priority = (
        await db.incidents.count_documents(
            high_priority_query
        )
    )

    # --------------------------------------------------------
    # Resolved incidents
    # --------------------------------------------------------

    resolved_query = {
        **_department_match(
            department_id
        ),
        "status": "Resolved",
    }

    resolved = (
        await db.incidents.count_documents(
            resolved_query
        )
    )

    # --------------------------------------------------------
    # Overdue incidents
    # --------------------------------------------------------

    now = datetime.now(
        timezone.utc
    )

    seven_days_ago = now - timedelta(
        days=7
    )

    overdue_query = {
        **_department_match(
            department_id
        ),
        "status": {
            "$nin": [
                "Resolved",
                "Closed",
            ]
        },
        "first_reported_at": {
            "$lt": seven_days_ago
        },
    }

    overdue = (
        await db.incidents.count_documents(
            overdue_query
        )
    )

    return {
        "total_assigned_complaints":
            total_complaints,

        "active_incidents":
            active_incidents,

        "high_priority_incidents":
            high_priority,

        "resolved_incidents":
            resolved,

        "overdue_incidents":
            overdue,
    }


# ============================================================
# OFFICER COMPLAINTS
# ============================================================

@router.get("/complaints")
async def officer_complaints(
    db=Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.officer
        )
    ),
):
    """
    Get complaints assigned to
    the officer's department.
    """

    assignment = await _get_officer_department(
        db,
        current_user.id,
    )

    department_id = assignment.get(
        "department_id"
    )

    complaints = await db.complaints.find(
        _assigned_department_match(
            department_id
        )
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
# OFFICER INCIDENTS
# ============================================================

@router.get("/incidents")
async def officer_incidents(
    category: str | None = None,
    priority: str | None = None,
    status: str | None = None,
    db=Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.officer
        )
    ),
):
    """
    Get incidents belonging to the
    officer's department.
    """

    assignment = await _get_officer_department(
        db,
        current_user.id,
    )

    department_id = assignment.get(
        "department_id"
    )

    query = _department_match(
        department_id
    )

    # --------------------------------------------------------
    # Category filter
    # --------------------------------------------------------

    if category:
        query["category"] = category

    # --------------------------------------------------------
    # Priority filter
    # --------------------------------------------------------

    if priority:

        query["$or"] = [
            {
                "approved_priority":
                    priority
            },
            {
                "recommended_priority":
                    priority
            },
        ]

    # --------------------------------------------------------
    # Status filter
    # --------------------------------------------------------

    if status:
        query["status"] = status

    # --------------------------------------------------------
    # Fetch incidents
    # --------------------------------------------------------

    incidents = await db.incidents.find(
        query
    ).sort(
        "last_reported_at",
        -1,
    ).to_list(
        length=None
    )

    return [
        await _incident_to_response(
            db,
            incident,
        )
        for incident in incidents
    ]


# ============================================================
# INCIDENT LINK CANDIDATES
# ============================================================

@router.get("/incident-candidates")
async def incident_candidates(
    db=Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.officer
        )
    ),
):
    """
    Get pending/citizen-linked incident
    candidates requiring officer review.
    """

    assignment = await _get_officer_department(
        db,
        current_user.id,
    )

    department_id = assignment.get(
        "department_id"
    )

    # --------------------------------------------------------
    # Find department incidents first
    # --------------------------------------------------------

    department_incidents = await db.incidents.find(
        _department_match(
            department_id
        )
    ).to_list(
        length=None
    )

    incident_ids = [
        incident["_id"]
        for incident in department_incidents
    ]

    if not incident_ids:
        return []

    # --------------------------------------------------------
    # Find pending/citizen-linked links
    # --------------------------------------------------------

    links = await db.incident_complaints.find(
        {
            "incident_id": {
                "$in": incident_ids
            },
            "link_status": {
                "$in": [
                    LinkStatus.pending.value,
                    LinkStatus.citizen_linked.value,
                ]
            },
        }
    ).to_list(
        length=None
    )

    results = []

    for link in links:

        complaint = await _find_complaint(
            db,
            link.get("complaint_id"),
        )

        incident = await _find_incident(
            db,
            link.get("incident_id"),
        )

        if not complaint or not incident:
            continue

        results.append(
            {
                "link_id":
                    str(link["_id"]),

                "complaint":
                    await _complaint_to_response(
                        db,
                        complaint,
                    ),

                "incident":
                    await _incident_to_response(
                        db,
                        incident,
                    ),

                "semantic_score":
                    link.get(
                        "semantic_score"
                    ),

                "spatial_score":
                    link.get(
                        "spatial_score"
                    ),

                "temporal_score":
                    link.get(
                        "temporal_score"
                    ),

                "combined_score":
                    link.get(
                        "combined_score"
                    ),

                "link_status":
                    link.get(
                        "link_status"
                    ),
            }
        )

    return results


# ============================================================
# CONFIRM INCIDENT LINK
# ============================================================

@router.post(
    "/incident-links/{link_id}/confirm"
)
async def confirm_link(
    link_id: str,
    db=Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.officer
        )
    ),
):
    """
    Confirm an AI-suggested or citizen-linked
    complaint-to-incident relationship.
    """

    link = await _find_link(
        db,
        link_id,
    )

    if not link:
        raise HTTPException(
            status_code=404,
            detail="Link not found",
        )

    # --------------------------------------------------------
    # Get incident
    # --------------------------------------------------------

    incident = await _find_incident(
        db,
        link.get("incident_id"),
    )

    if not incident:
        raise HTTPException(
            status_code=404,
            detail="Incident not found",
        )

    # --------------------------------------------------------
    # Verify officer department
    # --------------------------------------------------------

    assignment = await _get_officer_department(
        db,
        current_user.id,
    )

    officer_department = assignment.get(
        "department_id"
    )

    incident_department = incident.get(
        "department_id"
    )

    if (
        str(officer_department)
        != str(incident_department)
    ):
        raise HTTPException(
            status_code=403,
            detail=(
                "You are not authorized "
                "to review this incident"
            ),
        )

    # --------------------------------------------------------
    # Update link
    # --------------------------------------------------------

    now = datetime.now(
        timezone.utc
    )

    await db.incident_complaints.update_one(
        {
            "_id":
                link["_id"]
        },
        {
            "$set": {
                "link_status":
                    LinkStatus.confirmed.value,

                "reviewed_by":
                    str(current_user.id),

                "reviewed_at":
                    now,
            }
        },
    )

    # --------------------------------------------------------
    # Recalculate incident priority
    # --------------------------------------------------------

    updated_incident = await db.incidents.find_one(
        {
            "_id":
                incident["_id"]
        }
    )

    if updated_incident:

        await _recalculate_incident_priority(
            db,
            updated_incident,
        )

    return {
        "message":
            "Link confirmed"
    }


# ============================================================
# REJECT INCIDENT LINK
# ============================================================

@router.post(
    "/incident-links/{link_id}/reject"
)
async def reject_link(
    link_id: str,
    db=Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.officer
        )
    ),
):
    """
    Reject an AI-suggested or citizen-linked
    complaint-to-incident relationship.
    """

    link = await _find_link(
        db,
        link_id,
    )

    if not link:
        raise HTTPException(
            status_code=404,
            detail="Link not found",
        )

    # --------------------------------------------------------
    # Get incident
    # --------------------------------------------------------

    incident = await _find_incident(
        db,
        link.get("incident_id"),
    )

    if not incident:
        raise HTTPException(
            status_code=404,
            detail="Incident not found",
        )

    # --------------------------------------------------------
    # Verify officer department
    # --------------------------------------------------------

    assignment = await _get_officer_department(
        db,
        current_user.id,
    )

    officer_department = assignment.get(
        "department_id"
    )

    incident_department = incident.get(
        "department_id"
    )

    if (
        str(officer_department)
        != str(incident_department)
    ):
        raise HTTPException(
            status_code=403,
            detail=(
                "You are not authorized "
                "to review this incident"
            ),
        )

    # --------------------------------------------------------
    # Reject link
    # --------------------------------------------------------

    now = datetime.now(
        timezone.utc
    )

    await db.incident_complaints.update_one(
        {
            "_id":
                link["_id"]
        },
        {
            "$set": {
                "link_status":
                    LinkStatus.rejected.value,

                "reviewed_by":
                    str(current_user.id),

                "reviewed_at":
                    now,
            }
        },
    )

    return {
        "message":
            "Link rejected"
    }