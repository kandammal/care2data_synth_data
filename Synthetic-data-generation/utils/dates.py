"""
Date and time utilities for SDTM data generation.
"""

from datetime import date, datetime, timedelta
from typing import Optional, Union


def to_iso_date(d: Union[date, datetime, str, None]) -> str:
    """Convert to ISO 8601 date string (YYYY-MM-DD)."""
    if d is None:
        return ""
    if isinstance(d, str):
        return d[:10] if len(d) >= 10 else d
    if isinstance(d, datetime):
        return d.date().isoformat()
    if isinstance(d, date):
        return d.isoformat()
    return str(d)[:10]


def to_iso_datetime(dt: Union[date, datetime, str, None]) -> str:
    """Convert to ISO 8601 datetime string."""
    if dt is None:
        return ""
    if isinstance(dt, str):
        return dt
    if isinstance(dt, datetime):
        return dt.isoformat()
    if isinstance(dt, date):
        return datetime.combine(dt, datetime.min.time()).isoformat()
    return str(dt)


def parse_date(date_str: str) -> Optional[date]:
    """Parse an ISO 8601 date string."""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str[:10]).date()
    except (ValueError, TypeError):
        return None


def derive_study_day(
    event_date: Union[date, datetime, str],
    reference_date: Union[date, datetime, str]
) -> Optional[int]:
    """
    Derive study day (--DY) from event date and reference date (RFSTDTC).
    
    SDTM Convention:
    - If event_date >= reference_date: DY = (event_date - reference_date) + 1
    - If event_date < reference_date: DY = (event_date - reference_date)
    - Day 1 is the reference date; there is no Day 0
    """
    if isinstance(event_date, str):
        event_date = parse_date(event_date)
    elif isinstance(event_date, datetime):
        event_date = event_date.date()
    
    if isinstance(reference_date, str):
        reference_date = parse_date(reference_date)
    elif isinstance(reference_date, datetime):
        reference_date = reference_date.date()
    
    if event_date is None or reference_date is None:
        return None
    
    delta_days = (event_date - reference_date).days
    
    if delta_days >= 0:
        return delta_days + 1
    else:
        return delta_days


def add_days(base_date: Union[date, datetime, str], days: int) -> date:
    """Add days to a base date."""
    if isinstance(base_date, str):
        base_date = parse_date(base_date)
    elif isinstance(base_date, datetime):
        base_date = base_date.date()
    
    if base_date is None:
        raise ValueError("Invalid base date")
    
    return base_date + timedelta(days=days)


def study_day_to_date(study_day: int, reference_date: Union[date, datetime, str]) -> date:
    """Convert study day back to calendar date."""
    if isinstance(reference_date, str):
        reference_date = parse_date(reference_date)
    elif isinstance(reference_date, datetime):
        reference_date = reference_date.date()
    
    if reference_date is None:
        raise ValueError("Invalid reference date")
    
    if study_day >= 1:
        return reference_date + timedelta(days=study_day - 1)
    else:
        return reference_date + timedelta(days=study_day)


# Aliases for compatibility
format_iso_date = to_iso_date
format_iso_datetime = to_iso_datetime
parse_iso_date = parse_date


def days_between(date1: Union[date, datetime, str], date2: Union[date, datetime, str]) -> int:
    """Calculate days between two dates (date2 - date1)."""
    if isinstance(date1, str):
        date1 = parse_date(date1)
    elif isinstance(date1, datetime):
        date1 = date1.date()
    
    if isinstance(date2, str):
        date2 = parse_date(date2)
    elif isinstance(date2, datetime):
        date2 = date2.date()
    
    if date1 is None or date2 is None:
        raise ValueError("Invalid dates")
    
    return (date2 - date1).days


def date_in_range(
    test_date: Union[date, datetime, str],
    start_date: Union[date, datetime, str],
    end_date: Union[date, datetime, str]
) -> bool:
    """Check if test_date is within [start_date, end_date] inclusive."""
    if isinstance(test_date, str):
        test_date = parse_date(test_date)
    elif isinstance(test_date, datetime):
        test_date = test_date.date()
    
    if isinstance(start_date, str):
        start_date = parse_date(start_date)
    elif isinstance(start_date, datetime):
        start_date = start_date.date()
    
    if isinstance(end_date, str):
        end_date = parse_date(end_date)
    elif isinstance(end_date, datetime):
        end_date = end_date.date()
    
    if test_date is None or start_date is None or end_date is None:
        return False
    
    return start_date <= test_date <= end_date
