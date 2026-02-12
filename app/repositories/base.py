"""
Generic base repository. Subclass per entity for type-safe data access.
"""
from typing import Generic, TypeVar, Type, Optional, List, Any, Dict

from sqlalchemy.orm import Session, Query

from app.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Base repository with common CRUD operations."""

    def __init__(self, model: Type[ModelType], db: Session):
        self.model = model
        self.db = db

    def get(self, id: Any) -> Optional[ModelType]:
        """Get a single record by primary key."""
        return self.db.query(self.model).filter(self.model.id == id).first()

    def get_multi(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        order_by: Optional[Any] = None,
    ) -> List[ModelType]:
        """Get multiple records with optional ordering and pagination."""
        q = self.db.query(self.model)
        if order_by is not None:
            q = q.order_by(order_by)
        return q.offset(skip).limit(limit).all()

    def count(self, query: Optional[Query] = None) -> int:
        """Count rows. If query given, count that; else count all."""
        if query is not None:
            return query.count()
        return self.db.query(self.model).count()

    def add(self, obj: ModelType) -> ModelType:
        """Add and flush (no commit). Caller or service should commit."""
        self.db.add(obj)
        self.db.flush()
        return obj

    def delete(self, obj: ModelType) -> None:
        """Delete and flush."""
        self.db.delete(obj)
        self.db.flush()
