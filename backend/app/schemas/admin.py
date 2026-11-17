from pydantic import BaseModel, EmailStr, Field


# ============================================================
# DEPARTMENT
# ============================================================

class DepartmentCreate(BaseModel):
    name: str = Field(
        ...,
        min_length=2,
        max_length=255,
    )

    description: str | None = None


class DepartmentUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=255,
    )

    description: str | None = None

    is_active: bool | None = None


# ============================================================
# OFFICER
# ============================================================

class OfficerCreate(BaseModel):
    full_name: str = Field(
        ...,
        min_length=2,
        max_length=255,
    )

    email: EmailStr

    password: str = Field(
        ...,
        min_length=6,
    )

    department_id: str

    jurisdiction_id: str | None = None


# ============================================================
# JURISDICTION
# ============================================================

class JurisdictionCreate(BaseModel):
    name: str = Field(
        ...,
        min_length=2,
        max_length=255,
    )

    center_latitude: float = Field(
        ...,
        ge=-90,
        le=90,
    )

    center_longitude: float = Field(
        ...,
        ge=-180,
        le=180,
    )

    radius_meters: float = Field(
        default=5000.0,
        gt=0,
    )

    department_id: str | None = None