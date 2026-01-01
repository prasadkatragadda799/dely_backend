# Dely B2B Grocery App - Backend API

FastAPI backend for Dely B2B Grocery Mobile Application.

## Features

- ✅ 50+ RESTful API endpoints
- ✅ JWT Authentication & Authorization
- ✅ PostgreSQL/MySQL Database Support
- ✅ Swagger UI Documentation
- ✅ Comprehensive Error Handling
- ✅ Pagination Support
- ✅ Hostinger Deployment Ready

## Tech Stack

- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - ORM for database
- **Alembic** - Database migrations
- **Pydantic** - Data validation
- **Python-JOSE** - JWT tokens
- **Passlib** - Password hashing

## Quick Start

### 1. Install Dependencies

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and update with your settings:

```bash
cp .env.example .env
```

Update the following in `.env`:
- `DATABASE_URL` - Your database connection string
- `SECRET_KEY` - A secure secret key for JWT
- Other configuration as needed

### 3. Database Setup

```bash
# Initialize Alembic (if not already done)
alembic init migrations

# Create initial migration
alembic revision --autogenerate -m "Initial migration"

# Apply migrations
alembic upgrade head
```

### 4. Run the Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Access API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### Authentication (6 endpoints)
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login user
- `POST /api/v1/auth/forgot-password` - Request password reset
- `POST /api/v1/auth/reset-password` - Reset password
- `POST /api/v1/auth/refresh-token` - Refresh access token
- `POST /api/v1/auth/logout` - Logout user

### Products (6 endpoints)
- `GET /api/v1/products` - Get all products (with filters)
- `GET /api/v1/products/{product_id}` - Get product details
- `GET /api/v1/products/search` - Search products
- `GET /api/v1/products/featured` - Get featured products
- `GET /api/v1/products/company/{company_name}` - Get products by company
- `GET /api/v1/products/brand/{brand_name}` - Get products by brand

### Companies & Brands (4 endpoints)
- `GET /api/v1/companies` - Get all companies
- `GET /api/v1/companies/{company_id}` - Get company details
- `GET /api/v1/companies/hul/brands` - Get HUL brands
- `GET /api/v1/brands/biscuits` - Get biscuit brands

### Categories (3 endpoints)
- `GET /api/v1/categories` - Get all categories
- `GET /api/v1/categories/shop` - Get shop categories
- `GET /api/v1/categories/{category_id}/products` - Get category products

### Cart (5 endpoints) - Requires Auth
- `GET /api/v1/cart` - Get user's cart
- `POST /api/v1/cart/add` - Add item to cart
- `PUT /api/v1/cart/update/{cart_item_id}` - Update cart item
- `DELETE /api/v1/cart/remove/{cart_item_id}` - Remove from cart
- `DELETE /api/v1/cart/clear` - Clear cart

### Orders (5 endpoints) - Requires Auth
- `POST /api/v1/orders` - Create order
- `GET /api/v1/orders` - Get user's orders
- `GET /api/v1/orders/{order_id}` - Get order details
- `POST /api/v1/orders/{order_id}/cancel` - Cancel order
- `GET /api/v1/orders/{order_id}/track` - Track order

### User Profile (3 endpoints) - Requires Auth
- `GET /api/v1/user/profile` - Get user profile
- `PUT /api/v1/user/profile` - Update profile
- `POST /api/v1/user/change-password` - Change password

### Wishlist (3 endpoints) - Requires Auth
- `GET /api/v1/wishlist` - Get wishlist
- `POST /api/v1/wishlist/add` - Add to wishlist
- `DELETE /api/v1/wishlist/remove/{product_id}` - Remove from wishlist

### Offers (3 endpoints)
- `GET /api/v1/offers` - Get all offers
- `GET /api/v1/offers/company` - Get company offers
- `GET /api/v1/offers/text-slides` - Get text slides

### Notifications (3 endpoints) - Requires Auth
- `GET /api/v1/notifications` - Get notifications
- `PUT /api/v1/notifications/{notification_id}/read` - Mark as read
- `PUT /api/v1/notifications/read-all` - Mark all as read

### KYC (3 endpoints)
- `POST /api/v1/kyc/verify-gst` - Verify GST number
- `POST /api/v1/kyc/submit` - Submit KYC
- `GET /api/v1/kyc/status` - Get KYC status

### Delivery (3 endpoints) - Requires Auth
- `GET /api/v1/delivery/locations` - Get delivery locations
- `POST /api/v1/delivery/locations` - Add delivery location
- `POST /api/v1/delivery/check-availability` - Check delivery availability

### Payments (2 endpoints) - Requires Auth
- `POST /api/v1/payments/initiate` - Initiate payment
- `POST /api/v1/payments/verify` - Verify payment

### Statistics (1 endpoint) - Requires Auth
- `GET /api/v1/stats/quick` - Get quick stats

## Project Structure

```
dely-backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app entry point
│   ├── config.py              # Configuration settings
│   ├── database.py            # Database connection
│   ├── models/                # SQLAlchemy models
│   ├── schemas/               # Pydantic schemas
│   ├── api/                   # API routes
│   │   └── v1/               # API version 1
│   ├── services/              # Business logic
│   ├── utils/                 # Utilities
│   └── middleware/            # Custom middleware
├── migrations/                # Alembic migrations
├── requirements.txt
├── alembic.ini
├── wsgi.py                    # WSGI entry for Hostinger
└── README.md
```

## Authentication

Most endpoints require authentication. Include the JWT token in the Authorization header:

```
Authorization: Bearer <your_access_token>
```

## Response Format

### Success Response
```json
{
    "success": true,
    "data": { ... },
    "message": "Optional message"
}
```

### Error Response
```json
{
    "success": false,
    "message": "Error message",
    "error": {
        "code": "ERROR_CODE",
        "details": "Additional details"
    }
}
```

## Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Hostinger Deployment

1. Upload project files to Hostinger
2. Create virtual environment: `python3 -m venv venv`
3. Install dependencies: `pip install -r requirements.txt`
4. Configure `.env` file with production settings
5. Run migrations: `alembic upgrade head`
6. In Hostinger control panel:
   - Set Python version (3.9+)
   - Set startup file: `wsgi.py`
   - Set working directory: `/home/username/dely-backend`
   - Set virtual environment: `/home/username/dely-backend/venv`

## Environment Variables

See `.env.example` for all available environment variables.

## Testing

Test the API using Swagger UI at `/docs` or use curl:

```bash
# Health check
curl http://localhost:8000/health

# Get products
curl http://localhost:8000/api/v1/products
```

## License

MIT

## Support

For issues or questions, please check the API documentation at `/docs` or contact the development team.

