#!/usr/bin/env python3
"""
Delete a user and all their associated data by phone number.

Usage:
    python scripts/delete_user.py "+91 79979 19145"
    python scripts/delete_user.py "7997919145"
    python scripts/delete_user.py "+917997919145"

Run from the dely_backend directory so the app config is on the path.
"""
import sys
import os
from typing import Optional

# Allow running from the dely_backend root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database import SessionLocal
from app.models.user import User
from app.models.order import Order
from app.models.cart import Cart
from app.models.kyc import KYC
from app.models.kyc_document import KYCDocument
from app.models.wishlist import Wishlist
from app.models.notification import Notification
from app.models.delivery_location import DeliveryLocation
from app.models.wallet import Wallet
from app.models.user_activity_log import UserActivityLog
from app.models.user_payment_method import UserPaymentMethod


def normalize_phone(raw: str) -> list[str]:
    """Return candidate phone strings to try against the DB."""
    digits = "".join(c for c in raw if c.isdigit())
    candidates = [raw.strip()]
    if digits:
        candidates += [
            digits,
            f"+{digits}",
            f"+91{digits[-10:]}",
            f"+91 {digits[-10:]}",
            f"91{digits[-10:]}",
            digits[-10:],
        ]
    return list(dict.fromkeys(candidates))  # deduplicate, preserve order


def find_user(db, phone_raw: str) -> Optional[User]:
    for candidate in normalize_phone(phone_raw):
        user = db.query(User).filter(User.phone == candidate).first()
        if user:
            print(f"  Found user with phone format: '{candidate}'")
            return user
    return None


def summarize(db, user: User) -> None:
    order_count = db.query(Order).filter(Order.user_id == user.id).count()
    cart_count = db.query(Cart).filter(Cart.user_id == user.id).count()
    kyc_count = db.query(KYC).filter(KYC.user_id == user.id).count()
    kyc_doc_count = db.query(KYCDocument).filter(KYCDocument.user_id == user.id).count()
    wishlist_count = db.query(Wishlist).filter(Wishlist.user_id == user.id).count()
    notif_count = db.query(Notification).filter(Notification.user_id == user.id).count()
    loc_count = db.query(DeliveryLocation).filter(DeliveryLocation.user_id == user.id).count()
    wallet = db.query(Wallet).filter(Wallet.user_id == user.id).first()
    log_count = db.query(UserActivityLog).filter(UserActivityLog.user_id == user.id).count()
    pm_count = db.query(UserPaymentMethod).filter(UserPaymentMethod.user_id == user.id).count()

    print(f"\n  User:              {user.name} ({user.email})")
    print(f"  Phone:             {user.phone}")
    print(f"  KYC status:        {user.kyc_status}")
    print(f"  Account active:    {user.is_active}")
    print(f"  Created:           {user.created_at}")
    print(f"\n  Data to be deleted:")
    print(f"    Orders:          {order_count}")
    print(f"    Cart items:      {cart_count}")
    print(f"    KYC records:     {kyc_count}")
    print(f"    KYC documents:   {kyc_doc_count}")
    print(f"    Wishlist items:  {wishlist_count}")
    print(f"    Notifications:   {notif_count}")
    print(f"    Saved addresses: {loc_count}")
    print(f"    Wallet:          {'yes' if wallet else 'no'}")
    print(f"    Payment methods: {pm_count}")
    print(f"    Activity logs:   {log_count}")


def delete_user(db, user: User) -> None:
    uid = user.id
    # Use raw SQL throughout to avoid SQLAlchemy loading the Order.status enum
    # (DB may still have uppercase enum values that cause LookupError on ORM load).
    steps = [
        # order children first (FK cascade would handle order_items but be explicit)
        ("order_items",          "DELETE FROM order_items WHERE order_id IN (SELECT id FROM orders WHERE user_id = :uid)"),
        ("order_status_history", "DELETE FROM order_status_history WHERE order_id IN (SELECT id FROM orders WHERE user_id = :uid)"),
        ("orders",               "DELETE FROM orders WHERE user_id = :uid"),
        ("carts",                "DELETE FROM carts WHERE user_id = :uid"),
        ("kyc_documents",        "DELETE FROM kyc_documents WHERE user_id = :uid"),
        ("kycs",                 "DELETE FROM kycs WHERE user_id = :uid"),
        ("wishlists",            "DELETE FROM wishlists WHERE user_id = :uid"),
        ("notifications",        "DELETE FROM notifications WHERE user_id = :uid"),
        ("delivery_locations",   "DELETE FROM delivery_locations WHERE user_id = :uid"),
        ("wallet_transactions",  "DELETE FROM wallet_transactions WHERE wallet_id IN (SELECT id FROM wallets WHERE user_id = :uid)"),
        ("wallets",              "DELETE FROM wallets WHERE user_id = :uid"),
        ("user_payment_methods", "DELETE FROM user_payment_methods WHERE user_id = :uid"),
        ("user_activity_logs",   "DELETE FROM user_activity_logs WHERE user_id = :uid"),
        ("users",                "DELETE FROM users WHERE id = :uid"),
    ]
    for label, sql in steps:
        result = db.execute(text(sql), {"uid": uid})
        print(f"    {label}: {result.rowcount} row(s) deleted")
    db.commit()
    print("\n  User and all associated data deleted successfully.")


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/delete_user.py \"<phone>\"")
        sys.exit(1)

    phone_raw = sys.argv[1]
    print(f"\nLooking up user with phone: {phone_raw}")

    db = SessionLocal()
    try:
        user = find_user(db, phone_raw)
        if not user:
            print(f"  No user found with phone '{phone_raw}' (tried multiple formats).")
            sys.exit(1)

        summarize(db, user)

        print(f"\nThis will PERMANENTLY DELETE the user and all data listed above.")
        confirm = input("Type 'yes' to confirm: ").strip().lower()
        if confirm != "yes":
            print("Aborted.")
            sys.exit(0)

        delete_user(db, user)
    finally:
        db.close()


if __name__ == "__main__":
    main()
