# -*- coding: iso8859-15 -*-
import os
import sys

appdir = os.path.abspath(os.path.dirname(__file__))
projdir = os.path.abspath(os.path.join(appdir, ".."))
projdir2 = os.path.abspath(os.path.join(appdir, "../.."))
if projdir not in sys.path:
    sys.path.append(appdir)
    sys.path.append(projdir)
    sys.path.append(projdir2)

from datetime import datetime
from sqlalchemy.orm import class_mapper, ColumnProperty, RelationshipProperty
from src.global_config.database import db


class BaseModel(db):
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
                    result[attr.key] = value.isoformat()
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
                            value.to_dict(visited)
                            if hasattr(value, "to_dict")
                            else value
                        )

        return result
