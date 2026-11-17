from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.auth import UserRegister, UserResponse, Token
from app.security.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
)


router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse)
async def register(
    data: UserRegister,
    db=Depends(get_db),
):
    # Check whether email already exists
    existing_user = await db.users.find_one({
        "email": data.email
    })

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered",
        )

    # Create MongoDB user document
    user = User(
        full_name=data.full_name,
        email=data.email,
        password_hash=get_password_hash(data.password),
        role=UserRole.citizen,
        phone=data.phone,
    )

    user_document = user.model_dump(exclude_none=True)

    # Insert into MongoDB
    result = await db.users.insert_one(user_document)

    # Use MongoDB ObjectId as the application ID
    user_document["id"] = str(result.inserted_id)

    return UserResponse(
        id=user_document["id"],
        full_name=user_document["full_name"],
        email=user_document["email"],
        role=user_document["role"],
        phone=user_document.get("phone"),
        created_at=user_document["created_at"],
    )


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db=Depends(get_db),
):
    # Find user by email
    user = await db.users.find_one({
        "email": form_data.username
    })

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
        )

    # Verify password
    if not verify_password(
        form_data.password,
        user["password_hash"],
    ):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
        )

    # MongoDB ObjectId -> string
    user_id = str(user["_id"])

    role = user.get(
        "role",
        UserRole.citizen.value,
    )

    token = create_access_token(
        data={
            "sub": user_id,
            "role": role,
        }
    )

    return {
        "access_token": token,
        "token_type": "bearer",
    }


@router.get(
    "/me",
    response_model=UserResponse,
)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    return current_user