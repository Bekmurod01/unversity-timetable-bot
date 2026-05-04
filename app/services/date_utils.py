"""Utilities for date calculations and timezone handling."""

from datetime import datetime, timedelta
import pytz
from app.config import get_settings


WEEK_DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
DAY_NAMES = {
    "monday": "Monday",
    "tuesday": "Tuesday",
    "wednesday": "Wednesday",
    "thursday": "Thursday",
    "friday": "Friday",
    "saturday": "Saturday",
    "sunday": "Sunday",
}


def get_current_date() -> datetime:
    """Get current date in configured timezone."""
    tz = pytz.timezone(get_settings().timezone)
    return datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)


def day_name_to_next_date(day_name: str) -> datetime:
    """
    Convert a day name (e.g., 'wednesday') to the next occurrence of that day.
    
    Returns a date (datetime at 00:00:00) in configured timezone.
    For example: if today is Monday and we ask for 'monday', it returns today.
    If today is Monday and we ask for 'sunday', it returns next Sunday.
    """
    day_name = day_name.lower().strip()
    
    if day_name not in WEEK_DAYS:
        raise ValueError(f"Invalid day name: {day_name}")
    
    current = get_current_date()
    target_day_index = WEEK_DAYS.index(day_name)
    current_day_index = current.weekday()
    
    # Calculate days to add
    # If target day is today, return today
    # If target day has passed this week, get it next week
    # If target day is upcoming, get it this week
    days_ahead = target_day_index - current_day_index
    if days_ahead < 0:  # Target day has passed this week
        days_ahead += 7
    
    return current + timedelta(days=days_ahead)


def format_date_with_day(date: datetime) -> str:
    """Format date as 📅 YYYY-MM-DD (Weekday)"""
    date_str = date.strftime("%Y-%m-%d")
    weekday = DAY_NAMES.get(WEEK_DAYS[date.weekday()], date.strftime("%A"))
    return f"📅 {date_str} ({weekday})"


def group_lessons_by_date(lessons: list, use_next_date: bool = True) -> dict[datetime, list]:
    """
    Group TimetableLesson objects by their actual date.
    
    Attaches a `date_obj` attribute to each lesson for sorting and display.
    
    Args:
        lessons: List of TimetableLesson objects with 'day' attribute
        use_next_date: If True, calculate next occurrence of weekday.
                      If False, add 1 week (used for weekly view).
    
    Returns:
        Dictionary with datetime keys and lesson lists as values,
        sorted chronologically by date (earliest to latest).
    """
    grouped = {}
    
    for lesson in lessons:
        # Convert day name to date and attach to lesson object
        if use_next_date:
            lesson_date = day_name_to_next_date(lesson.day)
        else:
            lesson_date = day_name_to_next_date(lesson.day)
        
        # Attach date_obj to lesson for later reference
        lesson.date_obj = lesson_date
        
        if lesson_date not in grouped:
            grouped[lesson_date] = []
        grouped[lesson_date].append(lesson)
    
    # Sort by date (chronologically: earliest to latest)
    return dict(sorted(grouped.items()))


def sort_lessons_by_date(lessons: list) -> list:
    """
    Sort lessons chronologically by their computed date.
    
    Attaches `date_obj` to each lesson and returns sorted list.
    
    Args:
        lessons: List of TimetableLesson objects with 'day' attribute
    
    Returns:
        List of lessons sorted chronologically by date (earliest to latest)
    """
    # Attach date_obj to each lesson
    for lesson in lessons:
        lesson.date_obj = day_name_to_next_date(lesson.day)
    
    # Sort by date, then by start_time
    return sorted(lessons, key=lambda x: (x.date_obj, x.start_time))
