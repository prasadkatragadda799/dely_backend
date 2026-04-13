"""
Central route registration. Add new API/Admin/Delivery routes here.
Keeps main.py clean and makes route discovery obvious.
"""
from fastapi import FastAPI
import logging
import os

from app.api.v1 import (
    auth,
    products,
    companies,
    categories,
    divisions,
    cart,
    orders,
    user,
    wishlist,
    offers,
    notifications,
    kyc,
    delivery,
    maps,
    payments,
    stats,
)
from app.api.v1 import (
    admin_auth,
    admin_products,
    admin_orders,
    admin_users,
    admin_kyc,
    admin_companies,
    admin_categories,
    admin_divisions,
    admin_offers,
    admin_analytics,
    admin_upload,
    admin_reports,
    admin_sellers,
    seller_products,
    seller_resources,
    admin_settings,
    admin_management,
    admin_invoices,
    admin_import,
    delivery_auth,
    delivery_orders,
    delivery_dashboard,
    admin_delivery,
)
from app.web import legal_routes

logger = logging.getLogger(__name__)


def register_routes(app: FastAPI) -> None:
    """Register all API, Admin, and Delivery routers on the app."""

    # Public / Mobile API (v1)
    api_v1_routes = [
        (auth.router, "/api/v1/auth", ["Authentication"]),
        (products.router, "/api/v1/products", ["Products"]),
        (companies.router, "/api/v1/companies", ["Companies"]),
        (categories.router, "/api/v1/categories", ["Categories"]),
        (divisions.router, "/api/v1/divisions", ["Divisions"]),
        (cart.router, "/api/v1/cart", ["Cart"]),
        (orders.router, "/api/v1/orders", ["Orders"]),
        (user.router, "/api/v1/user", ["User"]),
        (wishlist.router, "/api/v1/wishlist", ["Wishlist"]),
        (offers.router, "/api/v1/offers", ["Offers"]),
        (notifications.router, "/api/v1/notifications", ["Notifications"]),
        (kyc.router, "/api/v1/kyc", ["KYC"]),
        (delivery.router, "/api/v1/delivery", ["Delivery"]),
        (maps.router, "/api/v1/maps", ["Maps"]),
        (payments.router, "/api/v1/payments", ["Payments"]),
        (stats.router, "/api/v1/stats", ["Statistics"]),
    ]
    for router, prefix, tags in api_v1_routes:
        app.include_router(router, prefix=prefix, tags=tags)

    # Admin
    admin_routes = [
        (admin_auth.router, "/admin/auth", ["Admin Authentication"]),
        (admin_products.router, "/admin/products", ["Admin Products"]),
        (admin_orders.router, "/admin/orders", ["Admin Orders"]),
        (admin_users.router, "/admin/users", ["Admin Users"]),
        (admin_kyc.router, "/admin/kyc", ["Admin KYC"]),
        (admin_companies.router, "/admin", ["Admin Companies & Brands"]),
        (admin_companies.router, "/api/admin", ["Admin Companies & Brands"]),
        (admin_categories.router, "/admin/categories", ["Admin Categories"]),
        (admin_divisions.router, "/admin/divisions", ["Admin Divisions"]),
        (admin_offers.router, "/admin/offers", ["Admin Offers"]),
        (admin_analytics.router, "/admin/analytics", ["Admin Analytics"]),
        (admin_upload.router, "/admin/upload", ["Admin Upload"]),
        (admin_import.router, "/admin/import", ["Admin Import"]),
        (admin_reports.router, "/admin/reports", ["Admin Reports"]),
        (admin_sellers.router, "/admin/sellers", ["Admin Sellers"]),
        (seller_products.router, "/seller/products", ["Seller Products"]),
        (seller_resources.router, "/seller", ["Seller Resources"]),
        (admin_settings.router, "/admin/settings", ["Admin Settings"]),
        (admin_management.router, "/admin/admins", ["Admin Management"]),
        (admin_invoices.router, "/admin/orders", ["Admin Invoices"]),
        (admin_delivery.router, "/admin/delivery", ["Admin Delivery"]),
    ]
    for router, prefix, tags in admin_routes:
        app.include_router(router, prefix=prefix, tags=tags)

    # Delivery
    delivery_routes = [
        (delivery_auth.router, "/delivery/auth", ["Delivery Authentication"]),
        (delivery_auth.router, "/api/v1/delivery/auth", ["Delivery Authentication"]),
        (delivery_dashboard.router, "/delivery", ["Delivery Dashboard"]),
        (delivery_dashboard.router, "/api/v1/delivery", ["Delivery Dashboard"]),
        (delivery_orders.router, "/delivery/orders", ["Delivery Orders"]),
        (delivery_orders.router, "/api/v1/delivery/orders", ["Delivery Orders"]),
    ]
    for router, prefix, tags in delivery_routes:
        app.include_router(router, prefix=prefix, tags=tags)

    # Public legal HTML (e.g. https://delycart.in/privacy-policy)
    app.include_router(legal_routes.router)

    # Startup sanity check (helps debug "404 Not Found" due to version/deployment mismatch).
    # Enabled when DEBUG is on or when LOG_ROUTE_MATCHES=true is set.
    log_matches = os.getenv("LOG_ROUTE_MATCHES", "").lower() == "true"
    if log_matches:
        target_paths = {
            "/api/v1/auth/send-otp",
            "/api/v1/auth/send_otp",
            "/api/v1/auth/sendOtp",
            "/api/v1/auth/sendotp",
            "/api/v1/auth/verify-otp",
        }
        found = set()
        for r in app.router.routes:
            path = getattr(r, "path", None)
            methods = getattr(r, "methods", None)
            if isinstance(path, str) and path in target_paths and methods:
                found.add(path)

        missing = sorted(target_paths - found)
        if missing:
            logger.error(
                "Route registration check FAILED. Missing OTP routes: %s",
                ", ".join(missing),
            )
        else:
            logger.info("Route registration check OK. OTP routes are present.")
