"""
Script to create the first admin user
Run this script after running database migrations

Usage:
    python create_admin.py
"""
import sys
from app.database import SessionLocal
from app.models.admin import Admin, AdminRole
from app.utils.security import get_password_hash

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
        
        # Get admin details from user
        print("=" * 50)
        print("Create First Admin User")
        print("=" * 50)
        
        email = input("Enter admin email: ").strip()
        if not email:
            print("[ERROR] Email is required!")
            return
        
        # Check if email already exists
        existing = db.query(Admin).filter(Admin.email == email).first()
        if existing:
            print(f"[ERROR] Admin with email {email} already exists!")
            return
        
        password = input("Enter admin password (min 6 characters): ").strip()
        if len(password) < 6:
            print("[ERROR] Password must be at least 6 characters!")
            return
        
        name = input("Enter admin name: ").strip()
        if not name:
            print("[ERROR] Name is required!")
            return
        
        print("\nSelect role:")
        print("1. Super Admin (Full access)")
        print("2. Admin (All CRUD except admin management)")
        print("3. Manager (Product, Order, KYC management)")
        print("4. Support (View only, order status updates)")
        
        role_choice = input("Enter role number (1-4) [default: 1]: ").strip() or "1"
        
        role_map = {
            "1": AdminRole.SUPER_ADMIN,
            "2": AdminRole.ADMIN,
            "3": AdminRole.MANAGER,
            "4": AdminRole.SUPPORT
        }
        
        role = role_map.get(role_choice, AdminRole.SUPER_ADMIN)
        
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

