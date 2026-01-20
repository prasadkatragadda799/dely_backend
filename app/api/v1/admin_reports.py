"""
Admin Reports Endpoints
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from datetime import datetime, timedelta
from typing import Optional
import io
import csv

from app.database import get_db
from app.models.user import User
from app.models.admin import Admin
from app.schemas.admin_report import WeeklyLocationReportResponse, UserLocationSummary, WeeklyLocationReportSummary
from app.schemas.common import ResponseModel
from app.api.admin_deps import get_current_active_admin

router = APIRouter()


@router.get("/weekly/user-location", response_model=ResponseModel)
async def get_weekly_user_location_report(
    startDate: str = Query(..., description="Start date in YYYY-MM-DD format"),
    endDate: str = Query(..., description="End date in YYYY-MM-DD format"),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_active_admin)
):
    """
    Get weekly user location report showing active/inactive users by location.
    
    Active users are defined as users who have been active within the last 7 days.
    """
    try:
        # Parse dates
        start = datetime.strptime(startDate, "%Y-%m-%d")
        end = datetime.strptime(endDate, "%Y-%m-%d")
        
        # Validate date range
        if end < start:
            raise HTTPException(status_code=400, detail="End date must be after start date")
        
        # Calculate active threshold (7 days before end date)
        active_threshold = end - timedelta(days=7)
        
        # Get all users
        users = db.query(User).all()
        
        # Aggregate by location
        location_data = {}
        
        for user in users:
            city = user.city or "Unknown"
            state = user.state or "Unknown"
            location_key = f"{city}|{state}"
            
            if location_key not in location_data:
                location_data[location_key] = {
                    "city": city,
                    "state": state,
                    "activeUsers": 0,
                    "inactiveUsers": 0
                }
            
            # Check if user is active
            is_active = (
                user.is_active and 
                user.last_active_at is not None and 
                user.last_active_at >= active_threshold
            )
            
            if is_active:
                location_data[location_key]["activeUsers"] += 1
            else:
                location_data[location_key]["inactiveUsers"] += 1
        
        # Convert to list
        locations = list(location_data.values())
        
        # Calculate summary
        total_active = sum(loc["activeUsers"] for loc in locations)
        total_inactive = sum(loc["inactiveUsers"] for loc in locations)
        total_users = total_active + total_inactive
        
        summary = WeeklyLocationReportSummary(
            totalActive=total_active,
            totalInactive=total_inactive,
            totalUsers=total_users
        )
        
        report_data = WeeklyLocationReportResponse(
            locations=[UserLocationSummary(**loc) for loc in locations],
            summary=summary
        )
        
        return ResponseModel(
            success=True,
            data=report_data.model_dump(),
            message="Weekly user location report retrieved successfully"
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format. Use YYYY-MM-DD: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating report: {str(e)}")


@router.get("/weekly/user-location/export")
async def export_weekly_user_location_report(
    startDate: str = Query(..., description="Start date in YYYY-MM-DD format"),
    endDate: str = Query(..., description="End date in YYYY-MM-DD format"),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_active_admin)
):
    """
    Export weekly user location report as CSV file.
    """
    try:
        # Parse dates
        start = datetime.strptime(startDate, "%Y-%m-%d")
        end = datetime.strptime(endDate, "%Y-%m-%d")
        
        # Validate date range
        if end < start:
            raise HTTPException(status_code=400, detail="End date must be after start date")
        
        # Calculate active threshold (7 days before end date)
        active_threshold = end - timedelta(days=7)
        
        # Get all users
        users = db.query(User).all()
        
        # Aggregate by location
        location_data = {}
        
        for user in users:
            city = user.city or "Unknown"
            state = user.state or "Unknown"
            location_key = f"{city}|{state}"
            
            if location_key not in location_data:
                location_data[location_key] = {
                    "city": city,
                    "state": state,
                    "activeUsers": 0,
                    "inactiveUsers": 0
                }
            
            # Check if user is active
            is_active = (
                user.is_active and 
                user.last_active_at is not None and 
                user.last_active_at >= active_threshold
            )
            
            if is_active:
                location_data[location_key]["activeUsers"] += 1
            else:
                location_data[location_key]["inactiveUsers"] += 1
        
        # Convert to list and sort by city
        locations = sorted(location_data.values(), key=lambda x: (x["state"], x["city"]))
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(["City", "State", "Active Users", "Inactive Users", "Total Users"])
        
        # Write data rows
        total_active = 0
        total_inactive = 0
        
        for loc in locations:
            active = loc["activeUsers"]
            inactive = loc["inactiveUsers"]
            total = active + inactive
            
            total_active += active
            total_inactive += inactive
            
            writer.writerow([
                loc["city"],
                loc["state"],
                active,
                inactive,
                total
            ])
        
        # Write summary row
        writer.writerow([])
        writer.writerow(["TOTAL", "", total_active, total_inactive, total_active + total_inactive])
        
        # Get CSV content
        output.seek(0)
        csv_content = output.getvalue()
        
        # Create filename with date range
        filename = f"user_location_report_{startDate}_to_{endDate}.csv"
        
        # Return as downloadable file
        return StreamingResponse(
            io.BytesIO(csv_content.encode('utf-8')),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format. Use YYYY-MM-DD: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting report: {str(e)}")
