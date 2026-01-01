"""
Script to create admin user from environment variables
This is called automatically during startup if ADMIN_EMAIL and ADMIN_PASSWORD are set
"""
import sys
import os
from app.database import SessionLocal
from app.models.admin import Admin, AdminRole
from app.utils.security import get_password_hash
from app.config import settings

def create_admin_from_env():
    """Create admin user from environment variables"""
    db = SessionLocal()
    
    try:
        # Check if admin credentials are provided
        email = os.getenv("ADMIN_EMAIL", "").strip() or settings.ADMIN_EMAIL
        password = os.getenv("ADMIN_PASSWORD", "").strip() or settings.ADMIN_PASSWORD
        name = os.getenv("ADMIN_NAME", "").strip() or settings.ADMIN_NAME
        role_str = os.getenv("ADMIN_ROLE", "").strip() or settings.ADMIN_ROLE
        
        if not email or not password:
            return False  # No credentials provided, skip creation
        
        # Check if admin already exists
        try:
            existing_admin = db.query(Admin).filter(Admin.email == email).first()
            if existing_admin:
                return False  # Admin already exists
        except Exception:
            # Table doesn't exist yet
            return False
        
        # Validate password
        if len(password) < 6:
            print(f"[WARNING] Admin password too short, skipping admin creation")
            return False
        
        # Parse role
        role_map = {
            "super_admin": AdminRole.SUPER_ADMIN,
            "admin": AdminRole.ADMIN,
            "manager": AdminRole.MANAGER,
            "support": AdminRole.SUPPORT
        }
        role = role_map.get(role_str.lower(), AdminRole.SUPER_ADMIN)
        
        # Create admin
        admin = Admin(
            email=email,
            password_hash=get_password_hash(password),
            name=name or "Admin",
            role=role,
            is_active=True
        )
        
        db.add(admin)
        db.commit()
        db.refresh(admin)
        
        print(f"[SUCCESS] Admin user created from environment variables!")
        print(f"   Email: {admin.email}")
        print(f"   Name: {admin.name}")
        print(f"   Role: {admin.role.value}")
        return True
        
    except Exception as e:
        db.rollback()
        print(f"[WARNING] Error creating admin from env: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    create_admin_from_env()

