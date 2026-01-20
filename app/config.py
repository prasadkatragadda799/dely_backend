from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import os
from functools import lru_cache


class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "Dely API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"  # Default to True for development
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")  # Default to development
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database
    # For SQLite (development): sqlite:///./dely.db
    # For PostgreSQL: postgresql://user:password@localhost:5432/dely_db
    # For MySQL: mysql+pymysql://user:password@localhost:3306/dely_db
    # For Render: Use DATABASE_URL from environment (automatically set by Render)
    # Render provides postgres:// URL which is automatically converted to postgresql://
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./dely.db")
    
    # JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "192837465")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8080,http://localhost:5173,http://localhost:5174,https://yourdomain.com")
    
    # Email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "noreply@dely.com"
    
    # External APIs
    GST_VERIFICATION_API_URL: str = "https://api.gst.gov.in"
    GST_API_KEY: str = ""
    GOOGLE_MAPS_API_KEY: str = os.getenv("GOOGLE_MAPS_API_KEY", "")
    
    # Payment Gateway
    PAYMENT_GATEWAY: str = "razorpay"
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    
    # File Upload
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 10485760  # 10MB
    ALLOWED_EXTENSIONS: str = "jpg,jpeg,png,pdf"
    
    # CDN / File Serving
    # In development, leave empty to use request base URL automatically
    # In production, set CDN_BASE_URL env var to your CDN URL (e.g., "https://cdn.dely.com")
    # If not set, defaults to empty string (will use request base URL)
    CDN_BASE_URL: str = os.getenv("CDN_BASE_URL", "")
    
    # Admin Default Credentials (for initial setup)
    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "")
    ADMIN_NAME: str = os.getenv("ADMIN_NAME", "Admin")
    ADMIN_ROLE: str = os.getenv("ADMIN_ROLE", "super_admin")  # super_admin, admin, manager, support
    
    # Seller/Company Information for Invoices
    SELLER_NAME: str = os.getenv("SELLER_NAME", "GRANARY WHOLESALE PRIVATE LIMITED")
    SELLER_ADDRESS_LINE1: str = os.getenv("SELLER_ADDRESS_LINE1", "No 331, Sarai Jagarnath")
    SELLER_ADDRESS_LINE2: str = os.getenv("SELLER_ADDRESS_LINE2", "pargana - Nizamabad, Tehsil - Sadar, Janpad & Dist - Azamgarh")
    SELLER_CITY: str = os.getenv("SELLER_CITY", "Azamgarh")
    SELLER_STATE: str = os.getenv("SELLER_STATE", "Uttar Pradesh")
    SELLER_PINCODE: str = os.getenv("SELLER_PINCODE", "276207")
    SELLER_GSTIN: str = os.getenv("SELLER_GSTIN", "09AAHCG7552R1ZP")
    SELLER_PAN: str = os.getenv("SELLER_PAN", "AAHCG7552R")
    SELLER_FSSAI: str = os.getenv("SELLER_FSSAI", "10019043002791")
    SELLER_FSSAI_LINK: str = os.getenv("SELLER_FSSAI_LINK", "https://foscos.fssai.gov.in/")
    SELLER_PHONE: str = os.getenv("SELLER_PHONE", "+91 XXXXX XXXXX")
    SELLER_EMAIL: str = os.getenv("SELLER_EMAIL", "company@example.com")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"  # Ignore extra fields in .env file
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

