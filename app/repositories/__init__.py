"""
Repository layer: data access only. No business logic.
Each repository wraps one or more models and exposes query methods.
"""
from app.repositories.base import BaseRepository
from app.repositories.product_repository import ProductRepository

__all__ = ["BaseRepository", "ProductRepository"]
