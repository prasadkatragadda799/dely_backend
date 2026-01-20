"""
Admin Settings Management Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID
from app.database import get_db
from app.schemas.common import ResponseModel
from app.schemas.settings import (
    GeneralSettings, PaymentSettings, DeliverySettings,
    TaxSettings, NotificationSettings, AllSettings
)
from app.models.settings import Settings
from app.models.admin import Admin, AdminRole
from app.models.category import Category
from app.api.admin_deps import require_manager_or_above, require_admin_or_super_admin, get_current_active_admin
from app.utils.admin_activity import log_admin_activity
import json
from pathlib import Path
from app.config import settings as app_settings

router = APIRouter()


def get_setting(db: Session, key: str) -> dict:
    """Get a setting by key"""
    setting = db.query(Settings).filter(Settings.key == key).first()
    return setting.value if setting else {}


def update_setting(db: Session, key: str, value: dict) -> None:
    """Update or create a setting"""
    setting = db.query(Settings).filter(Settings.key == key).first()
    if setting:
        setting.value = value
    else:
        setting = Settings(key=key, value=value)
        db.add(setting)
    db.commit()


# ===== General Settings =====

@router.get("/general", response_model=ResponseModel)
async def get_general_settings(
    admin: Admin = Depends(get_current_active_admin),
    db: Session = Depends(get_db)
):
    """Get general application settings"""
    settings = get_setting(db, "general")
    
    # Default values if not set
    if not settings:
        settings = {
            "appName": "Dely B2B",
            "appLogoUrl": None,
            "contactEmail": "support@dely.com",
            "contactPhone": "+91 1800 123 4567",
            "businessAddress": "123 Business Park, Mumbai, Maharashtra 400001"
        }
    
    return ResponseModel(
        success=True,
        data=settings,
        message="General settings retrieved successfully"
    )


@router.put("/general", response_model=ResponseModel)
async def update_general_settings(
    request: Request,
    appName: Optional[str] = Form(None),
    appLogo: Optional[UploadFile] = File(None),
    appLogoUrl: Optional[str] = Form(None),
    contactEmail: Optional[str] = Form(None),
    contactPhone: Optional[str] = Form(None),
    businessAddress: Optional[str] = Form(None),
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Update general application settings"""
    # Get current settings
    current_settings = get_setting(db, "general")
    
    # Update fields
    if appName is not None:
        current_settings["appName"] = appName
    
    # Handle logo upload
    if appLogo:
        # Upload file
        uploads_dir = Path(app_settings.UPLOAD_DIR) / "settings"
        uploads_dir.mkdir(parents=True, exist_ok=True)
        
        # Save file
        file_ext = appLogo.filename.split(".")[-1]
        file_name = f"logo.{file_ext}"
        file_path = uploads_dir / file_name
        
        with open(file_path, "wb") as f:
            content = await appLogo.read()
            f.write(content)
        
        # Generate URL
        logo_url = f"{app_settings.BASE_URL}/uploads/settings/{file_name}"
        current_settings["appLogoUrl"] = logo_url
    elif appLogoUrl is not None:
        current_settings["appLogoUrl"] = appLogoUrl
    
    if contactEmail is not None:
        current_settings["contactEmail"] = contactEmail
    
    if contactPhone is not None:
        current_settings["contactPhone"] = contactPhone
    
    if businessAddress is not None:
        current_settings["businessAddress"] = businessAddress
    
    # Save settings
    update_setting(db, "general", current_settings)
    
    # Log activity
    log_admin_activity(
        db=db,
        admin_id=admin.id,
        action="settings_updated",
        entity_type="settings",
        entity_id=None,
        details={"section": "general"},
        request=request
    )
    
    return ResponseModel(
        success=True,
        message="General settings updated successfully"
    )


# ===== Payment Settings =====

@router.get("/payment", response_model=ResponseModel)
async def get_payment_settings(
    admin: Admin = Depends(get_current_active_admin),
    db: Session = Depends(get_db)
):
    """Get payment settings"""
    settings = get_setting(db, "payment")
    
    # Default values
    if not settings:
        settings = {
            "creditEnabled": True,
            "upiEnabled": True,
            "bankTransferEnabled": True,
            "cashOnDeliveryEnabled": False,
            "defaultCreditLimit": 50000,
            "paymentTermsDays": 30
        }
    
    return ResponseModel(
        success=True,
        data=settings,
        message="Payment settings retrieved successfully"
    )


@router.put("/payment", response_model=ResponseModel)
async def update_payment_settings(
    settings_data: PaymentSettings,
    request: Request,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Update payment settings"""
    # Get current settings
    current_settings = get_setting(db, "payment")
    
    # Update fields
    if settings_data.creditEnabled is not None:
        current_settings["creditEnabled"] = settings_data.creditEnabled
    if settings_data.upiEnabled is not None:
        current_settings["upiEnabled"] = settings_data.upiEnabled
    if settings_data.bankTransferEnabled is not None:
        current_settings["bankTransferEnabled"] = settings_data.bankTransferEnabled
    if settings_data.cashOnDeliveryEnabled is not None:
        current_settings["cashOnDeliveryEnabled"] = settings_data.cashOnDeliveryEnabled
    if settings_data.defaultCreditLimit is not None:
        current_settings["defaultCreditLimit"] = settings_data.defaultCreditLimit
    if settings_data.paymentTermsDays is not None:
        current_settings["paymentTermsDays"] = settings_data.paymentTermsDays
    
    # Save settings
    update_setting(db, "payment", current_settings)
    
    # Log activity
    log_admin_activity(
        db=db,
        admin_id=admin.id,
        action="settings_updated",
        entity_type="settings",
        entity_id=None,
        details={"section": "payment"},
        request=request
    )
    
    return ResponseModel(
        success=True,
        message="Payment settings updated successfully"
    )


# ===== Delivery Settings =====

@router.get("/delivery", response_model=ResponseModel)
async def get_delivery_settings(
    admin: Admin = Depends(get_current_active_admin),
    db: Session = Depends(get_db)
):
    """Get delivery settings"""
    settings = get_setting(db, "delivery")
    
    # Default values
    if not settings:
        settings = {
            "standardDeliveryCharge": 100,
            "freeDeliveryThreshold": 5000,
            "deliveryTimeSlots": "Morning: 9 AM - 12 PM\nAfternoon: 12 PM - 4 PM\nEvening: 4 PM - 8 PM",
            "serviceablePincodes": ["400001", "400002", "400003"]
        }
    
    return ResponseModel(
        success=True,
        data=settings,
        message="Delivery settings retrieved successfully"
    )


@router.put("/delivery", response_model=ResponseModel)
async def update_delivery_settings(
    settings_data: DeliverySettings,
    request: Request,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Update delivery settings"""
    # Get current settings
    current_settings = get_setting(db, "delivery")
    
    # Update fields
    if settings_data.standardDeliveryCharge is not None:
        current_settings["standardDeliveryCharge"] = settings_data.standardDeliveryCharge
    if settings_data.freeDeliveryThreshold is not None:
        current_settings["freeDeliveryThreshold"] = settings_data.freeDeliveryThreshold
    if settings_data.deliveryTimeSlots is not None:
        current_settings["deliveryTimeSlots"] = settings_data.deliveryTimeSlots
    if settings_data.serviceablePincodes is not None:
        current_settings["serviceablePincodes"] = settings_data.serviceablePincodes
    
    # Save settings
    update_setting(db, "delivery", current_settings)
    
    # Log activity
    log_admin_activity(
        db=db,
        admin_id=admin.id,
        action="settings_updated",
        entity_type="settings",
        entity_id=None,
        details={"section": "delivery"},
        request=request
    )
    
    return ResponseModel(
        success=True,
        message="Delivery settings updated successfully"
    )


# ===== Tax Settings =====

@router.get("/tax", response_model=ResponseModel)
async def get_tax_settings(
    admin: Admin = Depends(get_current_active_admin),
    db: Session = Depends(get_db)
):
    """Get tax/GST settings"""
    settings = get_setting(db, "tax")
    
    # Default values
    if not settings:
        settings = {
            "defaultGstRate": 18,
            "categoryGstRates": []
        }
    
    # Enrich category names if needed
    if settings.get("categoryGstRates"):
        category_ids = [rate["categoryId"] for rate in settings["categoryGstRates"]]
        categories = db.query(Category).filter(Category.id.in_(category_ids)).all()
        category_map = {str(cat.id): cat.name for cat in categories}
        
        for rate in settings["categoryGstRates"]:
            if rate["categoryId"] in category_map:
                rate["categoryName"] = category_map[rate["categoryId"]]
    
    return ResponseModel(
        success=True,
        data=settings,
        message="Tax settings retrieved successfully"
    )


@router.put("/tax", response_model=ResponseModel)
async def update_tax_settings(
    settings_data: TaxSettings,
    request: Request,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Update tax/GST settings"""
    # Get current settings
    current_settings = get_setting(db, "tax")
    
    # Update fields
    if settings_data.defaultGstRate is not None:
        current_settings["defaultGstRate"] = settings_data.defaultGstRate
    
    if settings_data.categoryGstRates is not None:
        # Validate category IDs
        category_ids = [rate.categoryId for rate in settings_data.categoryGstRates]
        categories = db.query(Category).filter(Category.id.in_(category_ids)).all()
        
        if len(categories) != len(category_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more category IDs are invalid"
            )
        
        # Convert to dict
        current_settings["categoryGstRates"] = [
            {
                "categoryId": rate.categoryId,
                "categoryName": rate.categoryName,
                "gstRate": rate.gstRate
            }
            for rate in settings_data.categoryGstRates
        ]
    
    # Save settings
    update_setting(db, "tax", current_settings)
    
    # Log activity
    log_admin_activity(
        db=db,
        admin_id=admin.id,
        action="settings_updated",
        entity_type="settings",
        entity_id=None,
        details={"section": "tax"},
        request=request
    )
    
    return ResponseModel(
        success=True,
        message="Tax settings updated successfully"
    )


# ===== Notification Settings =====

@router.get("/notifications", response_model=ResponseModel)
async def get_notification_settings(
    admin: Admin = Depends(get_current_active_admin),
    db: Session = Depends(get_db)
):
    """Get notification templates"""
    settings = get_setting(db, "notifications")
    
    # Default values
    if not settings:
        settings = {
            "emailTemplates": {
                "orderConfirmation": "Dear {customer_name},\n\nYour order #{order_number} has been confirmed.\nTotal Amount: ₹{total_amount}\n\nThank you for your business!",
                "orderShipped": "Dear {customer_name},\n\nYour order #{order_number} has been shipped.\nTracking Number: {tracking_number}\n\nExpected delivery: {delivery_date}",
                "orderDelivered": "Dear {customer_name},\n\nYour order #{order_number} has been delivered successfully.\n\nThank you for your business!",
                "orderCancelled": "Dear {customer_name},\n\nYour order #{order_number} has been cancelled.\nReason: {cancellation_reason}\n\nWe apologize for any inconvenience."
            },
            "smsTemplates": {
                "orderConfirmation": "Your order #{order_number} for ₹{total_amount} has been confirmed. Thank you!",
                "orderShipped": "Your order #{order_number} has been shipped. Track: {tracking_number}",
                "orderDelivered": "Your order #{order_number} has been delivered successfully. Thank you!",
                "orderCancelled": "Your order #{order_number} has been cancelled. Reason: {cancellation_reason}"
            }
        }
    
    return ResponseModel(
        success=True,
        data=settings,
        message="Notification settings retrieved successfully"
    )


@router.put("/notifications", response_model=ResponseModel)
async def update_notification_settings(
    settings_data: NotificationSettings,
    request: Request,
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Update notification templates"""
    # Get current settings
    current_settings = get_setting(db, "notifications")
    
    # Update email templates
    if settings_data.emailTemplates:
        if "emailTemplates" not in current_settings:
            current_settings["emailTemplates"] = {}
        
        if settings_data.emailTemplates.orderConfirmation is not None:
            current_settings["emailTemplates"]["orderConfirmation"] = settings_data.emailTemplates.orderConfirmation
        if settings_data.emailTemplates.orderShipped is not None:
            current_settings["emailTemplates"]["orderShipped"] = settings_data.emailTemplates.orderShipped
        if settings_data.emailTemplates.orderDelivered is not None:
            current_settings["emailTemplates"]["orderDelivered"] = settings_data.emailTemplates.orderDelivered
        if settings_data.emailTemplates.orderCancelled is not None:
            current_settings["emailTemplates"]["orderCancelled"] = settings_data.emailTemplates.orderCancelled
    
    # Update SMS templates
    if settings_data.smsTemplates:
        if "smsTemplates" not in current_settings:
            current_settings["smsTemplates"] = {}
        
        if settings_data.smsTemplates.orderConfirmation is not None:
            current_settings["smsTemplates"]["orderConfirmation"] = settings_data.smsTemplates.orderConfirmation
        if settings_data.smsTemplates.orderShipped is not None:
            current_settings["smsTemplates"]["orderShipped"] = settings_data.smsTemplates.orderShipped
        if settings_data.smsTemplates.orderDelivered is not None:
            current_settings["smsTemplates"]["orderDelivered"] = settings_data.smsTemplates.orderDelivered
        if settings_data.smsTemplates.orderCancelled is not None:
            current_settings["smsTemplates"]["orderCancelled"] = settings_data.smsTemplates.orderCancelled
    
    # Save settings
    update_setting(db, "notifications", current_settings)
    
    # Log activity
    log_admin_activity(
        db=db,
        admin_id=admin.id,
        action="settings_updated",
        entity_type="settings",
        entity_id=None,
        details={"section": "notifications"},
        request=request
    )
    
    return ResponseModel(
        success=True,
        message="Notification settings updated successfully"
    )


# ===== Unified Settings =====

@router.get("", response_model=ResponseModel)
async def get_all_settings(
    admin: Admin = Depends(get_current_active_admin),
    db: Session = Depends(get_db)
):
    """Get all settings in one request"""
    general_settings = get_setting(db, "general") or {}
    payment_settings = get_setting(db, "payment") or {}
    delivery_settings = get_setting(db, "delivery") or {}
    tax_settings = get_setting(db, "tax") or {}
    notification_settings = get_setting(db, "notifications") or {}
    
    return ResponseModel(
        success=True,
        data={
            "general": general_settings,
            "payment": payment_settings,
            "delivery": delivery_settings,
            "tax": tax_settings,
            "notifications": notification_settings
        },
        message="Settings retrieved successfully"
    )
