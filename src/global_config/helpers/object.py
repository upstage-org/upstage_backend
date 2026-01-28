import re
from sqlalchemy.ext.declarative import DeclarativeMeta
import arrow
from datetime import datetime


def snake_to_camel(snake_str):
    components = snake_str.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


def convert_keys_to_camel_case(data):
    if isinstance(data, dict):
        new_data = {}
        for key, value in data.items():
            new_key = snake_to_camel(key)
            new_data[new_key] = convert_keys_to_camel_case(value)
        return new_data
    elif isinstance(data, list):
        return [convert_keys_to_camel_case(item) for item in data]
    else:
        return data


def camel_to_snake(name: str) -> str:
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def get_naive_utc_now():
    """
    Get the current UTC time as a timezone-naive datetime.
    This ensures all datetimes in the backend are timezone-naive UTC.
    
    Returns:
        timezone-naive datetime in UTC
    """
    return arrow.utcnow().datetime.replace(tzinfo=None)


def normalize_datetime_to_naive_utc(dt):
    """
    Convert a datetime (timezone-aware or timezone-naive) to timezone-naive UTC.
    This ensures all datetime comparisons work correctly regardless of timezone awareness.
    
    Args:
        dt: datetime object (can be timezone-aware or timezone-naive)
    
    Returns:
        timezone-naive datetime in UTC, or None if dt is None
    """
    if dt is None:
        return None
    if dt.tzinfo is not None:
        # Convert timezone-aware datetime to UTC, then remove timezone info
        return arrow.get(dt).to('UTC').datetime.replace(tzinfo=None)
    # Already timezone-naive, assume it's UTC and return as-is
    return dt
