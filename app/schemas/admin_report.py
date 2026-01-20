from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class UserLocationSummary(BaseModel):
    """Summary of users by location"""
    city: str
    state: str
    activeUsers: int
    inactiveUsers: int
    
    class Config:
        from_attributes = True


class WeeklyLocationReportSummary(BaseModel):
    """Overall summary for weekly location report"""
    totalActive: int
    totalInactive: int
    totalUsers: int


class WeeklyLocationReportResponse(BaseModel):
    """Weekly user location report response"""
    locations: List[UserLocationSummary]
    summary: WeeklyLocationReportSummary


class UserActivityCreate(BaseModel):
    """Schema for creating user activity log"""
    activity_type: str  # 'login', 'order', 'view_product', 'app_open', etc.


class UserActivityResponse(BaseModel):
    """Response for user activity creation"""
    success: bool
    message: str
