from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.api.deps import get_current_user
from app.schemas.user import UserResponse, UserUpdate, ChangePassword
from app.schemas.common import ResponseModel
from app.models.user import User
from app.utils.security import verify_password, get_password_hash

router = APIRouter()


@router.get("/profile", response_model=ResponseModel)
def get_profile(current_user: User = Depends(get_current_user)):
    """Get user profile"""
    return ResponseModel(
        success=True,
        data=UserResponse.model_validate(current_user)
    )


@router.put("/profile", response_model=ResponseModel)
def update_profile(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user profile"""
    if user_data.name:
        current_user.name = user_data.name
    if user_data.phone:
        # Check if phone already exists
        existing_user = db.query(User).filter(
            User.phone == user_data.phone,
            User.id != current_user.id
        ).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Phone number already in use")
        current_user.phone = user_data.phone
    if user_data.business_name:
        current_user.business_name = user_data.business_name
    if user_data.address:
        current_user.address = user_data.address
    
    db.commit()
    db.refresh(current_user)
    
    return ResponseModel(
        success=True,
        data=UserResponse.model_validate(current_user),
        message="Profile updated successfully"
    )


@router.post("/change-password", response_model=ResponseModel)
def change_password(
    password_data: ChangePassword,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change user password"""
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    if password_data.new_password != password_data.confirm_password:
        raise HTTPException(status_code=400, detail="New passwords do not match")
    
    current_user.password_hash = get_password_hash(password_data.new_password)
    db.commit()
    
    return ResponseModel(success=True, message="Password changed successfully")

