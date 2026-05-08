from pydantic_settings import BaseSettings, SettingsConfigDict
import os
from functools import lru_cache

DEFAULT_ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
_debug_env = os.getenv("DEBUG")
DEFAULT_DEBUG = _debug_env.lower() == "true" if _debug_env is not None else DEFAULT_ENVIRONMENT != "production"


class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "Dely API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = DEFAULT_DEBUG
    ENVIRONMENT: str = DEFAULT_ENVIRONMENT
    
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
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS
    ALLOWED_ORIGINS: str = os.getenv(
        "ALLOWED_ORIGINS",
        # In production, don't assume localhost origins.
        # If ALLOWED_ORIGINS is not explicitly configured, we want the API
        # to remain functional (CORS will be handled as "allow all" by main.py).
        "" if DEFAULT_ENVIRONMENT == "production" else "http://localhost:3000,http://localhost:8080,http://localhost:5173,http://localhost:5174",
    )
    
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
    TWO_FACTOR_API_KEY: str = os.getenv("TWO_FACTOR_API_KEY", "")
    PLAYSTORE_TEST_PHONE: str = os.getenv("PLAYSTORE_TEST_PHONE", "7997919145")
    PLAYSTORE_TEST_OTP: str = os.getenv("PLAYSTORE_TEST_OTP", "654321")
    PLAYSTORE_TEST_REQUEST_ID: str = os.getenv(
        "PLAYSTORE_TEST_REQUEST_ID",
        "PLAYSTORE-OTP-SESSION",
    )
    
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
    # Optional absolute URL for invoice / admin (e.g. CDN or public uploads path)
    SELLER_LOGO_URL: str = os.getenv("SELLER_LOGO_URL", "")
    
    # Push notifications (Firebase Cloud Messaging)
    FCM_SERVICE_ACCOUNT_PATH: str = os.getenv("FCM_SERVICE_ACCOUNT_PATH", "")

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"  # Ignore extra fields in .env file
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

