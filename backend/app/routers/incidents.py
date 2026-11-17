from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId

from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import get_db
from app.models.user import User, UserRole
from app.models.incident import (
    IncidentStatus,
)
from app.schemas.incident import (
    IncidentResponse,
    PriorityUpdate,
    IncidentStatusUpdate,
)
from app.security.auth import (
    get_current_user,
    require_roles,
)
from app.services.status_service import (
    record_status_change,
)
from app.services.complaint_service import (
    _recalculate_incident_priority,
)
from app.ai.spatial import (
    haversine_distance_meters,
)


router = APIRouter(
    prefix="/api/incidents",
    tags=["incidents"],
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _to_object_id(value):
    """
    Convert a value to MongoDB ObjectId.
    Returns None when invalid.
    """

    if isinstance(value, ObjectId):
        return value

    try:
        return ObjectId(str(value))
    except (InvalidId, TypeError):
        return None


async def _find_incident(db, incident_id: str):
    """
    Find incident using MongoDB ObjectId.
    """

    object_id = _to_object_id(incident_id)

    if object_id is None:
        return None

    return await db.incidents.find_one(
        {
            "_id": object_id
        }
    )


async def _get_department_name(
    db,
    department_id,
):
    """
    Get department name.

    Supports both ObjectId and string IDs.
    """

    if department_id is None:
        return None

    # ObjectId
    if isinstance(department_id, ObjectId):

        department = await db.departments.find_one(
            {
                "_id": department_id
            }
        )

        if department:
            return department.get("name")

        return None

    # String ID
    department = await db.departments.find_one(
        {
            "_id": department_id
        }
    )

    if department:
        return department.get("name")

    # Try converting string -> ObjectId
    object_id = _to_object_id(
        department_id
    )

    if object_id:

        department = await db.departments.find_one(
            {
                "_id": object_id
            }
        )

        if department:
            return department.get("name")

    return None


async def _find_complaint(
    db,
    complaint_id,
):
    """
    Find complaint supporting both ObjectId
    and string representations.
    """

    if isinstance(complaint_id, ObjectId):

        complaint = await db.complaints.find_one(
            {
                "_id": complaint_id
            }
        )

        if complaint:
            return complaint

        return None

    # Try ObjectId
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

    # String fallback
    return await db.complaints.find_one(
        {
            "_id": complaint_id
        }
    )


async def _incident_to_response(
    db,
    incident: dict,
) -> dict:
    """
    Convert MongoDB incident document into
    IncidentResponse-compatible data.
    """

    incident_id = incident["_id"]

    # --------------------------------------------------------
    # Department
    # --------------------------------------------------------

    department_name = await _get_department_name(
        db,
        incident.get("department_id"),
    )

    # --------------------------------------------------------
    # Related complaints
    # --------------------------------------------------------

    links = await db.incident_complaints.find(
        {
            "incident_id": incident_id
        }
    ).to_list(
        length=None
    )

    # Backward compatibility for string IDs
    if not links:
        links = await db.incident_complaints.find(
            {
                "incident_id": str(incident_id)
            }
        ).to_list(
            length=None
        )

    complaint_ids = [
        link.get("complaint_id")
        for link in links
        if link.get("complaint_id") is not None
    ]

    complaints = []

    for complaint_id in complaint_ids:

        complaint = await _find_complaint(
            db,
            complaint_id,
        )

        if complaint:
            complaints.append(
                complaint
            )

    # --------------------------------------------------------
    # Support count
    # --------------------------------------------------------

    support_count = await db.incident_supports.count_documents(
        {
            "incident_id": incident_id
        }
    )

    # Fallback for string IDs
    if support_count == 0:
        support_count = await db.incident_supports.count_documents(
            {
                "incident_id": str(incident_id)
            }
        )

    # --------------------------------------------------------
    # Unique reporters
    # --------------------------------------------------------

    unique_reporters = len(
        set(
            str(c.get("citizen_id"))
            for c in complaints
            if c.get("citizen_id") is not None
        )
    )

    # --------------------------------------------------------
    # Response
    # --------------------------------------------------------

    return {
        "id": str(incident_id),

        "incident_number": incident.get(
            "incident_number",
            "",
        ),

        "title": incident.get(
            "title",
            "",
        ),

        "description": incident.get(
            "description",
            "",
        ),

        "category": incident.get(
            "category",
            "",
        ),

        "center_latitude": incident.get(
            "center_latitude",
            0.0,
        ),

        "center_longitude": incident.get(
            "center_longitude",
            0.0,
        ),

        "first_reported_at": incident.get(
            "first_reported_at"
        ),

        "last_reported_at": incident.get(
            "last_reported_at"
        ),

        "recommended_priority": incident.get(
            "recommended_priority",
            "Medium",
        ),

        "approved_priority": incident.get(
            "approved_priority"
        ),

        "status": incident.get(
            "status",
            IncidentStatus.under_review.value,
        ),

        "department_name": department_name,

        "complaint_count": len(
            complaints
        ),

        "support_count": support_count,

        "unique_reporters": unique_reporters,

        "resolution_remarks": incident.get(
            "resolution_remarks"
        ),
    }


# ============================================================
# MAP DATA
# ============================================================

@router.get("/map-data")
async def incident_map_data(
    category: str | None = None,
    priority: str | None = None,
    status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    jurisdiction_id: str | None = None,
    radius_km: float | None = Query(None, gt=0),
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """Return privacy-safe complaint points and distinct linked incidents."""
    if date_from and date_to and date_from > date_to:
        raise HTTPException(
            status_code=422,
            detail="date_from must be earlier than or equal to date_to",
        )

    jurisdiction_documents = await db.jurisdictions.find({}).to_list(length=None)
    jurisdictions = []
    for document in jurisdiction_documents:
        latitude = document.get("center_latitude")
        longitude = document.get("center_longitude")
        if not _valid_coordinates(latitude, longitude):
            continue
        jurisdictions.append({
            "id": str(document["_id"]),
            "name": document.get("name", "Unnamed jurisdiction"),
            "center_latitude": float(latitude),
            "center_longitude": float(longitude),
            "radius_meters": float(document.get("radius_meters") or 5000),
        })

    selected_jurisdiction = None
    if jurisdiction_id:
        jurisdiction_object_id = _to_object_id(jurisdiction_id)
        jurisdiction_query = {"_id": jurisdiction_object_id} if jurisdiction_object_id else {"_id": jurisdiction_id}
        selected_jurisdiction = await db.jurisdictions.find_one(jurisdiction_query)
        if not selected_jurisdiction:
            raise HTTPException(status_code=404, detail="Jurisdiction not found")

    if selected_jurisdiction:
        center_latitude = selected_jurisdiction.get("center_latitude")
        center_longitude = selected_jurisdiction.get("center_longitude")
    elif jurisdictions:
        center_latitude = jurisdictions[0]["center_latitude"]
        center_longitude = jurisdictions[0]["center_longitude"]
    else:
        center_latitude = 18.5204
        center_longitude = 73.8567

    if not _valid_coordinates(center_latitude, center_longitude):
        raise HTTPException(
            status_code=422,
            detail="Selected jurisdiction has invalid map coordinates",
        )

    complaint_query = {}
    if category:
        complaint_query["category"] = category
    if status:
        complaint_query["status"] = status
    if date_from or date_to:
        created_at_query = {}
        if date_from:
            created_at_query["$gte"] = date_from
        if date_to:
            created_at_query["$lte"] = date_to
        complaint_query["created_at"] = created_at_query

    if current_user.role == UserRole.officer:
        assignment = await db.officer_assignments.find_one({
            "officer_id": str(current_user.id)
        })
        if not assignment or not assignment.get("department_id"):
            return {
                "reports": [],
                "incidents": [],
                "total_reports": 0,
                "unmapped_reports": 0,
                "distinct_incidents": 0,
                "jurisdictions": jurisdictions,
                "center": {
                    "latitude": float(center_latitude),
                    "longitude": float(center_longitude),
                },
            }
        department_id = assignment["department_id"]
        department_values = [department_id, str(department_id)]
        department_object_id = _to_object_id(department_id)
        if department_object_id:
            department_values.append(department_object_id)
        complaint_query["assigned_department_id"] = {"$in": department_values}

    complaints = await db.complaints.find(complaint_query).sort(
        "created_at", -1
    ).to_list(length=None)
    complaint_ids = [complaint["_id"] for complaint in complaints]
    complaint_id_strings = [str(complaint_id) for complaint_id in complaint_ids]

    links = []
    if complaint_ids:
        links = await db.incident_complaints.find({
            "$or": [
                {"complaint_id": {"$in": complaint_ids}},
                {"complaint_id": {"$in": complaint_id_strings}},
            ]
        }).to_list(length=None)

    link_rank = {"confirmed": 2, "citizen_linked": 1, "pending": 0}
    links_by_complaint = {}
    for link in links:
        if link.get("link_status") == "rejected":
            continue
        complaint_key = str(link.get("complaint_id"))
        previous = links_by_complaint.get(complaint_key)
        current_rank = link_rank.get(link.get("link_status"), -1)
        previous_rank = link_rank.get(previous.get("link_status"), -1) if previous else -1
        current_score = link.get("combined_score") or 0
        previous_score = (previous.get("combined_score") or 0) if previous else 0
        if previous is None or current_rank > previous_rank or (
            current_rank == previous_rank and current_score > previous_score
        ):
            links_by_complaint[complaint_key] = link

    incident_ids = {
        str(link.get("incident_id"))
        for link in links_by_complaint.values()
        if link.get("incident_id") is not None
    }
    incident_object_ids = [
        object_id for value in incident_ids
        if (object_id := _to_object_id(value)) is not None
    ]
    incident_query = {"$or": [
        {"_id": {"$in": incident_object_ids}},
        {"_id": {"$in": list(incident_ids)}},
    ]} if incident_ids else {}
    incident_documents = await db.incidents.find(incident_query).to_list(length=None)
    incidents_by_id = {str(document["_id"]): document for document in incident_documents}

    reports = []
    unmapped_reports = 0
    for complaint in complaints:
        latitude = complaint.get("latitude")
        longitude = complaint.get("longitude")
        if not _valid_coordinates(latitude, longitude):
            unmapped_reports += 1
            continue

        distance = haversine_distance_meters(
            float(center_latitude),
            float(center_longitude),
            float(latitude),
            float(longitude),
        )
        if radius_km is not None and distance > radius_km * 1000:
            continue

        link = links_by_complaint.get(str(complaint["_id"]))
        incident_id = str(link.get("incident_id")) if link and link.get("incident_id") is not None else None
        incident = incidents_by_id.get(incident_id) if incident_id else None
        if incident is None:
            incident_id = None
        incident_priority = (
            (incident.get("approved_priority") or incident.get("recommended_priority"))
            if incident else None
        )
        if priority and incident_priority != priority:
            continue

        reports.append({
            "id": str(complaint["_id"]),
            "report_number": complaint.get("complaint_number", ""),
            "title": complaint.get("title", ""),
            "category": complaint.get("category", ""),
            "priority": incident_priority,
            "status": complaint.get("status", ""),
            "latitude": float(latitude),
            "longitude": float(longitude),
            "created_at": complaint.get("created_at"),
            "incident_id": incident_id,
            "incident_number": incident.get("incident_number") if incident else None,
            "incident_status": incident.get("status") if incident else None,
        })

    incident_report_counts = {}
    for report in reports:
        if report["incident_id"]:
            incident_report_counts[report["incident_id"]] = (
                incident_report_counts.get(report["incident_id"], 0) + 1
            )

    incident_points = []
    for incident_id in incident_report_counts:
        incident = incidents_by_id.get(incident_id)
        if not incident:
            continue
        latitude = incident.get("center_latitude")
        longitude = incident.get("center_longitude")
        if not _valid_coordinates(latitude, longitude):
            continue
        incident_points.append({
            "id": incident_id,
            "incident_number": incident.get("incident_number", ""),
            "title": incident.get("title", ""),
            "category": incident.get("category", ""),
            "priority": incident.get("approved_priority") or incident.get("recommended_priority"),
            "status": incident.get("status", ""),
            "latitude": float(latitude),
            "longitude": float(longitude),
            "complaint_count": incident_report_counts[incident_id],
        })

    return {
        "reports": reports,
        "incidents": incident_points,
        "total_reports": len(reports),
        "unmapped_reports": unmapped_reports,
        "distinct_incidents": len(incident_report_counts),
        "jurisdictions": jurisdictions,
        "center": {
            "latitude": float(center_latitude),
            "longitude": float(center_longitude),
        },
    }


def _valid_coordinates(latitude, longitude):
    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except (TypeError, ValueError):
        return False
    return (
        -90 <= latitude <= 90
        and -180 <= longitude <= 180
        and (latitude != 0 or longitude != 0)
    )


# ============================================================
# NEARBY INCIDENTS
# ============================================================

@router.get(
    "/nearby",
    response_model=list[IncidentResponse],
)
async def nearby_incidents(
    latitude: float = Query(...),
    longitude: float = Query(...),
    radius_km: float = Query(
        5.0,
        gt=0,
    ),
    category: str | None = None,
    priority: str | None = None,
    status: str | None = None,
    db=Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    """
    Find incidents near a geographic point.
    """

    incidents = await db.incidents.find(
        {}
    ).to_list(
        length=None
    )

    results = []

    for incident in incidents:

        center_latitude = incident.get(
            "center_latitude"
        )

        center_longitude = incident.get(
            "center_longitude"
        )

        if (
            center_latitude is None
            or center_longitude is None
        ):
            continue

        distance = haversine_distance_meters(
            latitude,
            longitude,
            center_latitude,
            center_longitude,
        )

        # Radius filter
        if distance > radius_km * 1000:
            continue

        # Category filter
        if (
            category
            and incident.get("category")
            != category
        ):
            continue

        # Priority filter
        incident_priority = (
            incident.get("approved_priority")
            or incident.get(
                "recommended_priority"
            )
        )

        if (
            priority
            and incident_priority != priority
        ):
            continue

        # Status filter
        if (
            status
            and incident.get("status")
            != status
        ):
            continue

        response = await _incident_to_response(
            db,
            incident,
        )

        response[
            "distance_meters"
        ] = round(
            distance,
            1,
        )

        results.append(
            response
        )

    # Nearest incidents first
    results.sort(
        key=lambda item:
            item.get(
                "distance_meters",
                0,
            )
    )

    return results


# ============================================================
# LIST INCIDENTS
# ============================================================

@router.get(
    "",
    response_model=list[IncidentResponse],
)
async def list_incidents(
    category: str | None = None,
    priority: str | None = None,
    status: str | None = None,
    db=Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    """
    List incidents.

    Officers only see incidents assigned
    to their department.
    """

    query = {}

    # --------------------------------------------------------
    # Officer department restriction
    # --------------------------------------------------------

    if current_user.role == UserRole.officer:

        assignment = await db.officer_assignments.find_one(
            {
                "officer_id":
                    str(current_user.id)
            }
        )

        if assignment:

            department_id = assignment.get(
                "department_id"
            )

            query["department_id"] = (
                department_id
            )

        else:
            # Officer without assignment
            return []

    # --------------------------------------------------------
    # Category
    # --------------------------------------------------------

    if category:
        query["category"] = category

    # --------------------------------------------------------
    # Priority
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
    # Status
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
# GET SINGLE INCIDENT
# ============================================================

@router.get(
    "/{incident_id}"
)
async def get_incident(
    incident_id: str,
    db=Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    """
    Get complete incident details including:

    - Related complaints
    - Link scores
    - Priority explanation
    - Status history
    - Citizen support status
    """

    incident = await _find_incident(
        db,
        incident_id,
    )

    if not incident:
        raise HTTPException(
            status_code=404,
            detail="Incident not found",
        )

    incident_object_id = incident["_id"]

    # --------------------------------------------------------
    # Related complaint links
    # --------------------------------------------------------

    links = await db.incident_complaints.find(
        {
            "incident_id":
                incident_object_id
        }
    ).to_list(
        length=None
    )

    if not links:
        links = await db.incident_complaints.find(
            {
                "incident_id":
                    str(incident_object_id)
            }
        ).to_list(
            length=None
        )

    complaints = []

    for link in links:

        complaint = await _find_complaint(
            db,
            link.get("complaint_id"),
        )

        if not complaint:
            continue

        complaints.append(
            {
                "id": str(
                    complaint["_id"]
                ),

                "complaint_number":
                    complaint.get(
                        "complaint_number",
                        "",
                    ),

                "title":
                    complaint.get(
                        "title",
                        "",
                    ),

                "description":
                    complaint.get(
                        "description",
                        "",
                    ),

                "latitude":
                    complaint.get(
                        "latitude"
                    ),

                "longitude":
                    complaint.get(
                        "longitude"
                    ),

                "created_at":
                    complaint.get(
                        "created_at"
                    ),

                "status":
                    complaint.get(
                        "status"
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

    # --------------------------------------------------------
    # Latest priority assessment
    # --------------------------------------------------------

    latest_priority = await db.priority_assessments.find_one(
        {
            "incident_id":
                incident_object_id
        },
        sort=[
            (
                "created_at",
                -1,
            )
        ],
    )

    if latest_priority is None:

        latest_priority = await db.priority_assessments.find_one(
            {
                "incident_id":
                    str(incident_object_id)
            },
            sort=[
                (
                    "created_at",
                    -1,
                )
            ],
        )

    # --------------------------------------------------------
    # Status history
    # --------------------------------------------------------

    history = await db.status_history.find(
        {
            "entity_type": "incident",
            "entity_id": incident_object_id,
        }
    ).sort(
        "created_at",
        1,
    ).to_list(
        length=None
    )

    if not history:

        history = await db.status_history.find(
            {
                "entity_type": "incident",
                "entity_id":
                    str(incident_object_id),
            }
        ).sort(
            "created_at",
            1,
        ).to_list(
            length=None
        )

    # --------------------------------------------------------
    # Citizen support status
    # --------------------------------------------------------

    user_supported = False

    if current_user.role == UserRole.citizen:

        support = await db.incident_supports.find_one(
            {
                "incident_id":
                    incident_object_id,
                "citizen_id":
                    str(current_user.id),
            }
        )

        if support is None:

            support = await db.incident_supports.find_one(
                {
                    "incident_id":
                        str(incident_object_id),
                    "citizen_id":
                        str(current_user.id),
                }
            )

        user_supported = (
            support is not None
        )

    # --------------------------------------------------------
    # Base incident response
    # --------------------------------------------------------

    incident_response = (
        await _incident_to_response(
            db,
            incident,
        )
    )

    return {
        **incident_response,

        "complaints":
            complaints,

        "priority_explanation":
            (
                latest_priority.get(
                    "explanation"
                )
                if latest_priority
                else None
            ),

        "status_history": [
            {
                "previous_status":
                    item.get(
                        "previous_status"
                    ),

                "new_status":
                    item.get(
                        "new_status"
                    ),

                "remarks":
                    item.get(
                        "remarks"
                    ),

                "created_at":
                    item.get(
                        "created_at"
                    ),
            }
            for item in history
        ],

        "user_supported":
            user_supported,
    }


# ============================================================
# SUPPORT INCIDENT
# ============================================================

@router.post(
    "/{incident_id}/support"
)
async def support_incident(
    incident_id: str,
    db=Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.citizen
        )
    ),
):
    """
    Citizen supports an incident.

    Support count contributes to priority
    recommendation.
    """

    incident = await _find_incident(
        db,
        incident_id,
    )

    if not incident:
        raise HTTPException(
            status_code=404,
            detail="Incident not found",
        )

    incident_object_id = incident["_id"]

    # --------------------------------------------------------
    # Check existing support
    # --------------------------------------------------------

    existing = await db.incident_supports.find_one(
        {
            "incident_id":
                incident_object_id,
            "citizen_id":
                str(current_user.id),
        }
    )

    if existing is None:

        existing = await db.incident_supports.find_one(
            {
                "incident_id":
                    str(incident_object_id),
                "citizen_id":
                    str(current_user.id),
            }
        )

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Already supporting this incident",
        )

    # --------------------------------------------------------
    # Create support
    # --------------------------------------------------------

    await db.incident_supports.insert_one(
        {
            "incident_id":
                incident_object_id,
            "citizen_id":
                str(current_user.id),
            "created_at":
                datetime.now(timezone.utc),
        }
    )

    # --------------------------------------------------------
    # Recalculate priority
    # --------------------------------------------------------

    updated_incident = await db.incidents.find_one(
        {
            "_id":
                incident_object_id
        }
    )

    if updated_incident:

        await _recalculate_incident_priority(
            db,
            updated_incident,
        )

    return {
        "message": "Support recorded"
    }


# ============================================================
# WITHDRAW INCIDENT SUPPORT
# ============================================================

@router.delete(
    "/{incident_id}/support"
)
async def withdraw_support(
    incident_id: str,
    db=Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.citizen
        )
    ),
):
    """
    Citizen withdraws support from an incident.
    """

    incident = await _find_incident(
        db,
        incident_id,
    )

    if not incident:
        raise HTTPException(
            status_code=404,
            detail="Incident not found",
        )

    incident_object_id = incident["_id"]

    # --------------------------------------------------------
    # Find support
    # --------------------------------------------------------

    support = await db.incident_supports.find_one(
        {
            "incident_id":
                incident_object_id,
            "citizen_id":
                str(current_user.id),
        }
    )

    if support is None:

        support = await db.incident_supports.find_one(
            {
                "incident_id":
                    str(incident_object_id),
                "citizen_id":
                    str(current_user.id),
            }
        )

    if not support:
        raise HTTPException(
            status_code=404,
            detail="Support not found",
        )

    # --------------------------------------------------------
    # Delete support
    # --------------------------------------------------------

    await db.incident_supports.delete_one(
        {
            "_id":
                support["_id"]
        }
    )

    # --------------------------------------------------------
    # Recalculate priority
    # --------------------------------------------------------

    updated_incident = await db.incidents.find_one(
        {
            "_id":
                incident_object_id
        }
    )

    if updated_incident:

        await _recalculate_incident_priority(
            db,
            updated_incident,
        )

    return {
        "message": "Support withdrawn"
    }


# ============================================================
# UPDATE INCIDENT PRIORITY
# ============================================================

@router.patch(
    "/{incident_id}/priority"
)
async def update_priority(
    incident_id: str,
    data: PriorityUpdate,
    db=Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.officer,
            UserRole.admin,
        )
    ),
):
    """
    Officer/Admin approves or changes
    the recommended incident priority.
    """

    incident = await _find_incident(
        db,
        incident_id,
    )

    if not incident:
        raise HTTPException(
            status_code=404,
            detail="Incident not found",
        )

    now = datetime.now(timezone.utc)

    # --------------------------------------------------------
    # Update approved priority
    # --------------------------------------------------------

    await db.incidents.update_one(
        {
            "_id":
                incident["_id"]
        },
        {
            "$set": {
                "approved_priority":
                    data.approved_priority,

                "priority_change_reason":
                    data.reason,

                "updated_at":
                    now,
            }
        },
    )

    # --------------------------------------------------------
    # Return updated incident
    # --------------------------------------------------------

    updated_incident = await db.incidents.find_one(
        {
            "_id":
                incident["_id"]
        }
    )

    return await _incident_to_response(
        db,
        updated_incident,
    )


# ============================================================
# UPDATE INCIDENT STATUS
# ============================================================

@router.patch(
    "/{incident_id}/status"
)
async def update_incident_status(
    incident_id: str,
    data: IncidentStatusUpdate,
    db=Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.officer,
            UserRole.admin,
        )
    ),
):
    """
    Update incident status.

    The status is propagated to all linked complaints.
    Citizens are notified about the change.
    """

    incident = await _find_incident(
        db,
        incident_id,
    )

    if not incident:
        raise HTTPException(
            status_code=404,
            detail="Incident not found",
        )

    incident_object_id = incident["_id"]

    previous_status = incident.get(
        "status"
    )

    now = datetime.now(timezone.utc)

    # --------------------------------------------------------
    # Update incident
    # --------------------------------------------------------

    incident_update = {
        "status":
            data.status,

        "updated_at":
            now,
    }

    if data.resolution_remarks:
        incident_update[
            "resolution_remarks"
        ] = data.resolution_remarks

    await db.incidents.update_one(
        {
            "_id":
                incident_object_id
        },
        {
            "$set":
                incident_update
        },
    )

    # --------------------------------------------------------
    # Incident status history
    # --------------------------------------------------------

    await record_status_change(
        db=db,
        entity_type="incident",
        entity_id=str(
            incident_object_id
        ),
        previous_status=
            previous_status,
        new_status=
            data.status,
        changed_by=
            str(current_user.id),
        remarks=
            data.remarks,
    )

    # --------------------------------------------------------
    # Find linked complaints
    # --------------------------------------------------------

    links = await db.incident_complaints.find(
        {
            "incident_id":
                incident_object_id
        }
    ).to_list(
        length=None
    )

    if not links:

        links = await db.incident_complaints.find(
            {
                "incident_id":
                    str(incident_object_id)
            }
        ).to_list(
            length=None
        )

    # --------------------------------------------------------
    # Propagate status to complaints
    # --------------------------------------------------------

    from app.services.notification_service import (
        create_notification,
    )

    for link in links:

        complaint = await _find_complaint(
            db,
            link.get("complaint_id"),
        )

        if not complaint:
            continue

        complaint_object_id = complaint[
            "_id"
        ]

        complaint_previous_status = (
            complaint.get("status")
        )

        # Update complaint
        await db.complaints.update_one(
            {
                "_id":
                    complaint_object_id
            },
            {
                "$set": {
                    "status":
                        data.status,

                    "updated_at":
                        now,
                }
            },
        )

        # Complaint status history
        await record_status_change(
            db=db,
            entity_type="complaint",
            entity_id=str(
                complaint_object_id
            ),
            previous_status=
                complaint_previous_status,
            new_status=
                data.status,
            changed_by=
                str(current_user.id),
            remarks=(
                f"Updated via incident "
                f"{incident.get('incident_number', '')}"
            ),
        )

        # Citizen notification
        citizen_id = complaint.get(
            "citizen_id"
        )

        if citizen_id:

            await create_notification(
                db=db,
                user_id=str(
                    citizen_id
                ),
                title="Complaint Updated",
                message=(
                    f"Your complaint "
                    f"{complaint.get('complaint_number', '')} "
                    f"status: {data.status}"
                ),
            )

    # --------------------------------------------------------
    # Return updated incident
    # --------------------------------------------------------

    updated_incident = await db.incidents.find_one(
        {
            "_id":
                incident_object_id
        }
    )

    return await _incident_to_response(
        db,
        updated_incident,
    )