from collections import Counter
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId

from fastapi import APIRouter, Depends, HTTPException

from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.admin import (
    DepartmentCreate,
    DepartmentUpdate,
    OfficerCreate,
    JurisdictionCreate,
)
from app.security.auth import (
    require_roles,
    get_password_hash,
)
from app.routers.complaints import _complaint_to_response
from app.routers.incidents import _incident_to_response


router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
)


# ============================================================
# HELPERS
# ============================================================

def _to_object_id(value):
    """
    Convert a value to MongoDB ObjectId.
    Returns None if conversion fails.
    """

    if isinstance(value, ObjectId):
        return value

    if value is None:
        return None

    try:
        return ObjectId(str(value))
    except (InvalidId, TypeError):
        return None


def _serialize_document(document):
    """
    Convert MongoDB ObjectId values into strings
    so FastAPI can return them as JSON.
    """

    if not document:
        return document

    result = dict(document)

    if "_id" in result:
        result["id"] = str(result.pop("_id"))

    return result


async def _find_department(db, dept_id):
    """
    Find department using either:
    - MongoDB ObjectId
    - string ID
    """

    if dept_id is None:
        return None

    object_id = _to_object_id(dept_id)

    # First try ObjectId
    if object_id:
        department = await db.departments.find_one(
            {
                "_id": object_id
            }
        )

        if department:
            return department

    # Then try string ID
    return await db.departments.find_one(
        {
            "_id": dept_id
        }
    )


async def _find_jurisdiction(db, jurisdiction_id):
    """
    Find jurisdiction using either:
    - MongoDB ObjectId
    - string ID
    """

    if jurisdiction_id is None:
        return None

    object_id = _to_object_id(jurisdiction_id)

    # First try ObjectId
    if object_id:
        jurisdiction = await db.jurisdictions.find_one(
            {
                "_id": object_id
            }
        )

        if jurisdiction:
            return jurisdiction

    # Then try string ID
    return await db.jurisdictions.find_one(
        {
            "_id": jurisdiction_id
        }
    )


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@router.get("/dashboard")
async def admin_dashboard(
    db=Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.admin)
    ),
):
    """
    Admin dashboard statistics.
    """

    # --------------------------------------------------------
    # Basic counts
    # --------------------------------------------------------

    total_complaints = await db.complaints.count_documents({})

    total_incidents = await db.incidents.count_documents({})

    resolved_incidents = await db.incidents.count_documents(
        {
            "status": "Resolved"
        }
    )

    pending_incidents = await db.incidents.count_documents(
        {
            "status": {
                "$nin": [
                    "Resolved",
                    "Closed",
                ]
            }
        }
    )

    # --------------------------------------------------------
    # Complaints by category
    # --------------------------------------------------------

    category_counter = Counter()

    complaints = await db.complaints.find(
        {},
        {
            "category": 1,
            "assigned_department_id": 1,
            "suggested_department_id": 1,
        },
    ).to_list(length=None)

    for complaint in complaints:

        category = (
            complaint.get("category")
            or "Unknown"
        )

        category_counter[category] += 1

    complaints_by_category = [
        {
            "category": category,
            "count": count,
        }
        for category, count
        in sorted(category_counter.items())
    ]

    # --------------------------------------------------------
    # Incidents by priority
    # --------------------------------------------------------

    priority_counter = Counter()

    incidents = await db.incidents.find(
        {},
        {
            "approved_priority": 1,
            "recommended_priority": 1,
        },
    ).to_list(length=None)

    for incident in incidents:

        priority = (
            incident.get("approved_priority")
            or incident.get("recommended_priority")
            or "Unknown"
        )

        priority_counter[priority] += 1

    incidents_by_priority = [
        {
            "priority": priority,
            "count": count,
        }
        for priority, count
        in sorted(priority_counter.items())
    ]

    # --------------------------------------------------------
    # Complaints by department
    # --------------------------------------------------------

    department_counter = Counter()

    for complaint in complaints:

        department_id = complaint.get(
            "assigned_department_id"
        )

        # No department assigned
        if department_id is None:

            department_name = "Unassigned"

        else:

            # Resolve department using the same
            # ObjectId/string logic used elsewhere
            department = await _find_department(
                db,
                department_id,
            )

            if department:

                department_name = (
                    department.get("name")
                    or "Unknown"
                )

            else:

                department_name = "Unassigned"

        department_counter[department_name] += 1

    complaints_by_department = [
        {
            "department": department,
            "count": count,
        }
        for department, count
        in sorted(department_counter.items())
    ]

    # --------------------------------------------------------
    # Monthly complaints
    # --------------------------------------------------------

    monthly_counter = Counter()

    all_complaints = await db.complaints.find(
        {},
        {
            "created_at": 1,
        },
    ).to_list(length=None)

    for complaint in all_complaints:

        created_at = complaint.get(
            "created_at"
        )

        if isinstance(created_at, datetime):

            monthly_counter[
                created_at.month
            ] += 1

    monthly_complaints = [
        {
            "month": month,
            "count": count,
        }
        for month, count
        in sorted(monthly_counter.items())
    ]

    # --------------------------------------------------------
    # Final dashboard response
    # --------------------------------------------------------

    return {
        "total_complaints": total_complaints,

        "total_incidents": total_incidents,

        "resolved_incidents": resolved_incidents,

        "pending_incidents": pending_incidents,

        "complaints_by_category":
            complaints_by_category,

        "incidents_by_priority":
            incidents_by_priority,

        "complaints_by_department":
            complaints_by_department,

        "monthly_complaints":
            monthly_complaints,
    }


# ============================================================
# DEPARTMENTS
# ============================================================

@router.get("/departments")
async def list_departments(
    db=Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.admin)
    ),
):
    """
    List all departments.
    """

    departments = await db.departments.find(
        {}
    ).sort(
        "name",
        1,
    ).to_list(
        length=None
    )

    return [
        _serialize_document(department)
        for department in departments
    ]


@router.post("/departments")
async def create_department(
    data: DepartmentCreate,
    db=Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.admin)
    ),
):
    """
    Create a new department.
    """

    # Prevent duplicate names
    existing = await db.departments.find_one(
        {
            "name": data.name
        }
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Department already exists",
        )

    now = datetime.now(timezone.utc)

    document = {
        "name": data.name,
        "description": data.description,
        "is_active": True,
        "created_at": now,
    }

    result = await db.departments.insert_one(
        document
    )

    document["_id"] = result.inserted_id

    return _serialize_document(document)


@router.patch("/departments/{dept_id}")
async def update_department(
    dept_id: str,
    data: DepartmentUpdate,
    db=Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.admin)
    ),
):
    """
    Update department information.
    """

    department = await _find_department(
        db,
        dept_id,
    )

    if not department:
        raise HTTPException(
            status_code=404,
            detail="Department not found",
        )

    update_data = {}

    if data.name is not None:
        update_data["name"] = data.name

    if data.description is not None:
        update_data["description"] = data.description

    if data.is_active is not None:
        update_data["is_active"] = data.is_active

    if not update_data:
        return _serialize_document(
            department
        )

    update_data["updated_at"] = (
        datetime.now(timezone.utc)
    )

    await db.departments.update_one(
        {
            "_id": department["_id"]
        },
        {
            "$set": update_data
        },
    )

    updated = await db.departments.find_one(
        {
            "_id": department["_id"]
        }
    )

    return _serialize_document(updated)


# ============================================================
# OFFICERS
# ============================================================

@router.get("/officers")
async def list_officers(
    db=Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.admin)
    ),
):
    """
    List all officers with their
    department and jurisdiction.
    """

    officers = await db.users.find(
        {
            "role": UserRole.officer.value
        }
    ).sort(
        "full_name",
        1,
    ).to_list(
        length=None
    )

    result = []

    for officer in officers:

        officer_id = str(
            officer["_id"]
        )

        assignment = (
            await db.officer_assignments.find_one(
                {
                    "officer_id": officer_id
                }
            )
        )

        department_id = None
        department_name = None
        jurisdiction_id = None

        if assignment:

            department_id = assignment.get(
                "department_id"
            )

            jurisdiction_id = assignment.get(
                "jurisdiction_id"
            )

            department = await _find_department(
                db,
                department_id,
            )

            if department:

                department_name = (
                    department.get("name")
                )

        result.append(
            {
                "id": officer_id,

                "full_name":
                    officer.get("full_name"),

                "email":
                    officer.get("email"),

                "department_id":
                    (
                        str(department_id)
                        if department_id is not None
                        else None
                    ),

                "department_name":
                    department_name,

                "jurisdiction_id":
                    (
                        str(jurisdiction_id)
                        if jurisdiction_id is not None
                        else None
                    ),
            }
        )

    return result


@router.post("/officers")
async def create_officer(
    data: OfficerCreate,
    db=Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.admin)
    ),
):
    """
    Create an officer account and
    assign department/jurisdiction.
    """

    # --------------------------------------------------------
    # Check email
    # --------------------------------------------------------

    existing = await db.users.find_one(
        {
            "email": data.email
        }
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Email already exists",
        )

    # --------------------------------------------------------
    # Verify department
    # --------------------------------------------------------

    department = await _find_department(
        db,
        data.department_id,
    )

    if not department:
        raise HTTPException(
            status_code=404,
            detail="Department not found",
        )

    # --------------------------------------------------------
    # Verify jurisdiction if supplied
    # --------------------------------------------------------

    if data.jurisdiction_id:

        jurisdiction = await _find_jurisdiction(
            db,
            data.jurisdiction_id,
        )

        if not jurisdiction:
            raise HTTPException(
                status_code=404,
                detail="Jurisdiction not found",
            )

    # --------------------------------------------------------
    # Create user
    # --------------------------------------------------------

    now = datetime.now(timezone.utc)

    user_document = {
        "full_name": data.full_name,

        "email": data.email,

        "password_hash":
            get_password_hash(
                data.password
            ),

        "role":
            UserRole.officer.value,

        "created_at": now,
    }

    user_result = await db.users.insert_one(
        user_document
    )

    officer_id = str(
        user_result.inserted_id
    )

    # --------------------------------------------------------
    # Create officer assignment
    # --------------------------------------------------------

    assignment_document = {
        "officer_id":
            officer_id,

        "department_id":
            str(data.department_id),
    }

    if data.jurisdiction_id:

        assignment_document[
            "jurisdiction_id"
        ] = str(
            data.jurisdiction_id
        )

    await db.officer_assignments.insert_one(
        assignment_document
    )

    return {
        "id": officer_id,

        "email": data.email,

        "full_name": data.full_name,
    }


# ============================================================
# JURISDICTIONS
# ============================================================

@router.get("/jurisdictions")
async def list_jurisdictions(
    db=Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.admin)
    ),
):
    """
    List all jurisdictions.
    """

    jurisdictions = await db.jurisdictions.find(
        {}
    ).sort(
        "name",
        1,
    ).to_list(
        length=None
    )

    return [
        _serialize_document(jurisdiction)
        for jurisdiction in jurisdictions
    ]


@router.post("/jurisdictions")
async def create_jurisdiction(
    data: JurisdictionCreate,
    db=Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.admin)
    ),
):
    """
    Create a jurisdiction.
    """

    document = data.model_dump(
        exclude_none=True
    )

    document["created_at"] = (
        datetime.now(timezone.utc)
    )

    # Store department ID consistently as string
    if document.get("department_id") is not None:

        document["department_id"] = str(
            document["department_id"]
        )

    result = await db.jurisdictions.insert_one(
        document
    )

    document["_id"] = result.inserted_id

    return _serialize_document(document)


# ============================================================
# ADMIN COMPLAINTS
# ============================================================

@router.get("/complaints")
async def admin_complaints(
    db=Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.admin)
    ),
):
    """
    List all complaints.
    """

    complaints = await db.complaints.find(
        {}
    ).sort(
        "created_at",
        -1,
    ).to_list(
        length=None
    )

    result = []

    for complaint in complaints:

        result.append(
            await _complaint_to_response(
                db,
                complaint,
            )
        )

    return result


# ============================================================
# ADMIN INCIDENTS
# ============================================================

@router.get("/incidents")
async def admin_incidents(
    db=Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.admin)
    ),
):
    """
    List all incidents.
    """

    incidents = await db.incidents.find(
        {}
    ).sort(
        "last_reported_at",
        -1,
    ).to_list(
        length=None
    )

    result = []

    for incident in incidents:

        result.append(
            await _incident_to_response(
                db,
                incident,
            )
        )

    return result