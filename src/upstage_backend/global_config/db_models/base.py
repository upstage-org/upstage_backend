from datetime import datetime

from upstage_backend.global_config.helpers.clock import as_utc
from sqlalchemy.orm import ColumnProperty, DeclarativeBase, RelationshipProperty, class_mapper


class Base(DeclarativeBase):
    """
    SQLAlchemy 2.0 declarative base. Models declare typed attributes:
    `Mapped[...] = mapped_column(...)`, with the column arguments spelled
    out (type, nullable, default) rather than inferred from the annotation.
    """


class BaseModel(Base):
    __abstract__ = True

    def to_dict(self, visited=None):
        if visited is None:
            visited = set()

        # Avoid circular references
        if id(self) in visited:
            return None
        visited.add(id(self))

        result = {}
        mapper = class_mapper(self.__class__)

        # Include column attributes
        for attr in mapper.attrs:
            if isinstance(attr, ColumnProperty):
                value = getattr(self, attr.key)
                if isinstance(value, datetime):
                    # Always with the UTC offset, so clients never have to
                    # guess which zone a bare timestamp was written in.
                    result[attr.key] = as_utc(value).isoformat()
                else:
                    result[attr.key] = value

        # Include relationship attributes
        for attr in mapper.attrs:
            if isinstance(attr, RelationshipProperty):
                value = getattr(self, attr.key)
                if value is not None:
                    if isinstance(value, list):
                        result[attr.key] = [
                            item.to_dict(visited) if hasattr(item, "to_dict") else item
                            for item in value
                        ]
                    else:
                        result[attr.key] = (
                            value.to_dict(visited) if hasattr(value, "to_dict") else value
                        )

        return result
