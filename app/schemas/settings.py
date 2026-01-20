"""
Settings Schemas
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict


# General Settings
class GeneralSettings(BaseModel):
    appName: Optional[str] = None
    appLogoUrl: Optional[str] = None
    contactEmail: Optional[EmailStr] = None
    contactPhone: Optional[str] = None
    businessAddress: Optional[str] = None


# Payment Settings
class PaymentSettings(BaseModel):
    creditEnabled: Optional[bool] = None
    upiEnabled: Optional[bool] = None
    bankTransferEnabled: Optional[bool] = None
    cashOnDeliveryEnabled: Optional[bool] = None
    defaultCreditLimit: Optional[float] = None
    paymentTermsDays: Optional[int] = None


# Delivery Settings
class DeliverySettings(BaseModel):
    standardDeliveryCharge: Optional[float] = None
    freeDeliveryThreshold: Optional[float] = None
    deliveryTimeSlots: Optional[str] = None
    serviceablePincodes: Optional[List[str]] = None


# Tax Settings
class CategoryGstRate(BaseModel):
    categoryId: str
    categoryName: str
    gstRate: float = Field(ge=0, le=100)


class TaxSettings(BaseModel):
    defaultGstRate: Optional[float] = Field(None, ge=0, le=100)
    categoryGstRates: Optional[List[CategoryGstRate]] = None


# Notification Settings
class EmailTemplates(BaseModel):
    orderConfirmation: Optional[str] = None
    orderShipped: Optional[str] = None
    orderDelivered: Optional[str] = None
    orderCancelled: Optional[str] = None


class SmsTemplates(BaseModel):
    orderConfirmation: Optional[str] = None
    orderShipped: Optional[str] = None
    orderDelivered: Optional[str] = None
    orderCancelled: Optional[str] = None


class NotificationSettings(BaseModel):
    emailTemplates: Optional[EmailTemplates] = None
    smsTemplates: Optional[SmsTemplates] = None


# Unified Settings
class AllSettings(BaseModel):
    general: Optional[GeneralSettings] = None
    payment: Optional[PaymentSettings] = None
    delivery: Optional[DeliverySettings] = None
    tax: Optional[TaxSettings] = None
    notifications: Optional[NotificationSettings] = None


# Admin User Schemas
class AdminUserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(min_length=6)
    role: str = Field(pattern="^(super_admin|admin|manager|support|seller)$")


class AdminUserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=6)
    role: Optional[str] = Field(None, pattern="^(super_admin|admin|manager|support|seller)$")
    status: Optional[str] = Field(None, pattern="^(active|inactive)$")
    is_active: Optional[bool] = None  # Alternative to status


class AdminUserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str
    status: str
    lastLogin: Optional[str] = None
    createdAt: str
    updatedAt: str
    
    class Config:
        from_attributes = True
