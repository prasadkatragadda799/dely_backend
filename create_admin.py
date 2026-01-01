"""
Script to create the first admin user
Run this script after running database migrations

Usage:
    python create_admin.py

Environment Variables (optional):
    ADMIN_EMAIL - Admin email address
    ADMIN_PASSWORD - Admin password (min 6 characters)
    ADMIN_NAME - Admin name
    ADMIN_ROLE - Admin role (super_admin, admin, manager, support)
"""
import sys
import os
from app.database import SessionLocal
from app.models.admin import Admin, AdminRole
from app.utils.security import get_password_hash
from app.config import settings

def create_admin():
    """Create the first admin user"""
    db = SessionLocal()
    
    try:
        # Check if any admin already exists
        try:
            existing_admin = db.query(Admin).first()
            if existing_admin:
                print("[ERROR] Admin user already exists!")
                print(f"   Email: {existing_admin.email}")
                print("   Use the login endpoint to authenticate.")
                return
        except Exception as e:
            # Table doesn't exist - need to run migrations
            if "no such table" in str(e).lower():
                print("[ERROR] Admin table does not exist!")
                print("   Please run database migrations first:")
                print("   alembic upgrade head")
                return
            raise
        
        # Get admin details from environment variables or user input
        print("=" * 50)
        print("Create First Admin User")
        print("=" * 50)
        
        # Check environment variables first
        email = os.getenv("ADMIN_EMAIL", "").strip() or settings.ADMIN_EMAIL
        password = os.getenv("ADMIN_PASSWORD", "").strip() or settings.ADMIN_PASSWORD
        name = os.getenv("ADMIN_NAME", "").strip() or settings.ADMIN_NAME
        role_str = os.getenv("ADMIN_ROLE", "").strip() or settings.ADMIN_ROLE
        
        # If env vars are not set, get from user input
        if not email:
            email = input("Enter admin email: ").strip()
            if not email:
                print("[ERROR] Email is required!")
                return
        
        # Check if email already exists
        existing = db.query(Admin).filter(Admin.email == email).first()
        if existing:
            print(f"[ERROR] Admin with email {email} already exists!")
            return
        
        if not password:
            password = input("Enter admin password (min 6 characters): ").strip()
            if len(password) < 6:
                print("[ERROR] Password must be at least 6 characters!")
                return
        
        if not name:
            name = input("Enter admin name: ").strip()
            if not name:
                print("[ERROR] Name is required!")
                return
        
        # Parse role
        role_map = {
            "super_admin": AdminRole.SUPER_ADMIN,
            "admin": AdminRole.ADMIN,
            "manager": AdminRole.MANAGER,
            "support": AdminRole.SUPPORT,
            "1": AdminRole.SUPER_ADMIN,
            "2": AdminRole.ADMIN,
            "3": AdminRole.MANAGER,
            "4": AdminRole.SUPPORT
        }
        
        if not role_str or role_str not in role_map:
            print("\nSelect role:")
            print("1. Super Admin (Full access)")
            print("2. Admin (All CRUD except admin management)")
            print("3. Manager (Product, Order, KYC management)")
            print("4. Support (View only, order status updates)")
            
            role_choice = input("Enter role number (1-4) [default: 1]: ").strip() or "1"
            role = role_map.get(role_choice, AdminRole.SUPER_ADMIN)
        else:
            role = role_map.get(role_str.lower(), AdminRole.SUPER_ADMIN)
        
        # Create admin
        admin = Admin(
            email=email,
            password_hash=get_password_hash(password),
            name=name,
            role=role,
            is_active=True
        )
        
        db.add(admin)
        db.commit()
        db.refresh(admin)
        
        print("\n" + "=" * 50)
        print("[SUCCESS] Admin user created successfully!")
        print("=" * 50)
        print(f"   Email: {admin.email}")
        print(f"   Name: {admin.name}")
        print(f"   Role: {admin.role.value}")
        print(f"   ID: {admin.id}")
        print("\n[TIP] You can now login at: POST /admin/auth/login")
        print("=" * 50)
        
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Error creating admin: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    create_admin()

