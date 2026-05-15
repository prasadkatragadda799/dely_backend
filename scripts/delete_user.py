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

from app.database import SessionLocal
from app.models.user import User
from app.models.order import Order, OrderItem
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
    # Orders: order_items cascade from orders, status_history cascades from orders.
    # The ORM cascade="all, delete-orphan" on User.orders handles them.
    # But DB FK is SET NULL, so we must delete via ORM (not raw SQL DELETE on users).
    db.delete(user)
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
