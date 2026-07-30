from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..db import database, models
from ..schemas import auth as schemas
from ..core.security import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter()


@router.post("/register", response_model=schemas.TokenResponse)
def register(user_in: schemas.UserCreate, db: Session = Depends(database.get_db)):
    """Register a new user account."""
    # Check for existing username
    existing = db.query(models.User).filter(
        (models.User.username == user_in.username) | (models.User.email == user_in.email)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already registered"
        )
    
    # Determine role: first user is admin
    user_count = db.query(models.User).count()
    role = "admin" if user_count == 0 else "user"
    
    db_user = models.User(
        username=user_in.username,
        email=user_in.email,
        password_hash=hash_password(user_in.password),
        role=role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    token = create_access_token(data={"sub": str(db_user.id), "role": db_user.role})
    return schemas.TokenResponse(access_token=token, user=schemas.UserResponse.model_validate(db_user))


@router.post("/login", response_model=schemas.TokenResponse)
def login(creds: schemas.UserLogin, db: Session = Depends(database.get_db)):
    """Authenticate and return a JWT."""
    user = db.query(models.User).filter(models.User.username == creds.username).first()
    if not user or not verify_password(creds.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    token = create_access_token(data={"sub": str(user.id), "role": user.role})
    return schemas.TokenResponse(access_token=token, user=schemas.UserResponse.model_validate(user))


@router.get("/me", response_model=schemas.UserResponse)
def get_current_user_info(
    current_user: models.User = Depends(get_current_user)
):
    """Get current authenticated user info."""
    return current_user
