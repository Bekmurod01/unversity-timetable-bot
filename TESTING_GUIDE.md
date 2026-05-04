# Testing Guide - Timetable Date Display Features

## Quick Test Commands

### 1. Test Date Utilities Module
```bash
cd d:\University_time_table

# Test imports
python -c "from app.services.date_utils import get_current_date, day_name_to_next_date, format_date_with_day, group_lessons_by_date; print('✓ Imports successful')"

# Test current date
python -c "from app.services.date_utils import get_current_date, format_date_with_day; print('Today:', format_date_with_day(get_current_date()))"

# Test all weekday conversions
python -c "from app.services.date_utils import day_name_to_next_date, format_date_with_day; days=['monday','tuesday','wednesday','thursday','friday','saturday','sunday']; [print(f'{day:10} -> {format_date_with_day(day_name_to_next_date(day))}') for day in days]"
```

### 2. Test with Mock Lessons
```python
# Create test lesson objects
from datetime import time
from app.services.date_utils import group_lessons_by_date, format_date_with_day

class MockLesson:
    def __init__(self, day, subject, start_time, end_time, room, teacher):
        self.day = day
        self.subject = subject
        self.start_time = time.fromisoformat(start_time)
        self.end_time = time.fromisoformat(end_time)
        self.room = room
        self.teacher = teacher
        self.status = "active"
        self.group_name = "IT-202"

# Create test lessons
lessons = [
    MockLesson("monday", "Data Structures", "08:30", "09:15", "Room 205", "Dr. Smith"),
    MockLesson("wednesday", "Algorithms", "10:00", "11:30", "Lab 101", "Prof. Williams"),
    MockLesson("friday", "Web Development", "14:00", "15:30", "Room 301", "Ms. Johnson"),
]

# Test grouping
grouped = group_lessons_by_date(lessons)
for date, date_lessons in grouped.items():
    print(f"\n{format_date_with_day(date)}")
    for lesson in date_lessons:
        print(f"  {lesson.start_time}-{lesson.end_time}: {lesson.subject} ({lesson.room})")
```

### 3. Check File Syntax
```bash
# Compile Python files
python -m py_compile app/services/date_utils.py
python -m py_compile app/bot/handlers/timetable.py

# Check dependencies
pip show pytz
```

### 4. Test Timezone Handling
```bash
# Verify timezone configuration
python -c "from app.config import get_settings; print('Timezone:', get_settings().timezone)"

# Test with different times of week
# Manually change system time or mock datetime in tests
```

## Manual Testing Steps (With Bot Running)

### Scenario 1: Weekly Schedule
1. Start the bot
2. Send `/start` and complete registration
3. Click "📅 My Timetable"
4. Click "Weekly"
5. **Expected Output:**
   - Title includes "📅 Weekly schedule"
   - Lessons are grouped by date
   - Each date shows as "📅 YYYY-MM-DD (Weekday)"
   - Lessons are sorted by time within each date

### Scenario 2: Today's Schedule
1. In bot, click "📅 My Timetable"
2. Click "Today"
3. **Expected Output:**
   - Title shows today's date with format "📅 YYYY-MM-DD (Weekday)"
   - Only today's lessons shown
   - At least one lesson (if data exists)

### Scenario 3: Tomorrow's Schedule
1. In bot, click "📅 My Timetable"
2. Click "Tomorrow"
3. **Expected Output:**
   - Title shows tomorrow's date
   - Only tomorrow's lessons shown
   - Format matches "📅 YYYY-MM-DD (Weekday)"

### Scenario 4: Custom Day Selection
1. In bot, click "📅 My Timetable"
2. Click "Custom Day"
3. Click any day (e.g., "Wednesday")
4. **Expected Output:**
   - Shows actual date of that day
   - Format: "📅 YYYY-MM-DD (Wednesday)"
   - Shows lessons for that day

### Scenario 5: Edge Cases
1. **No lessons on a day**: Show "No lessons found"
2. **Multiple days with lessons**: Verify grouping and sorting
3. **Cancelled lessons**: Check ❌ icon displays
4. **Multiple groups**: Verify group name shows in weekly view

## Unit Test Template

```python
import pytest
from datetime import datetime, timedelta
from app.services.date_utils import (
    day_name_to_next_date,
    format_date_with_day,
    get_current_date,
    group_lessons_by_date,
)


def test_get_current_date():
    """Test that current date returns a date (00:00:00)"""
    date = get_current_date()
    assert date.hour == 0
    assert date.minute == 0
    assert date.second == 0


def test_day_name_to_next_date_today():
    """Test that current weekday returns today"""
    today = get_current_date()
    today_name = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"][today.weekday()]
    result = day_name_to_next_date(today_name)
    assert result == today


def test_day_name_to_next_date_future():
    """Test that future weekday returns correct date"""
    today = get_current_date()
    # Get tomorrow
    tomorrow = today + timedelta(days=1)
    tomorrow_name = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"][tomorrow.weekday()]
    result = day_name_to_next_date(tomorrow_name)
    assert result == tomorrow


def test_format_date_with_day():
    """Test date formatting"""
    date = get_current_date()
    result = format_date_with_day(date)
    assert "📅" in result
    assert "2026-05-04" in result or "2026-05-" in result  # Today's date
    assert "(" in result and ")" in result  # Has weekday parentheses


def test_invalid_day_name():
    """Test that invalid day name raises error"""
    with pytest.raises(ValueError):
        day_name_to_next_date("invalid")


def test_group_lessons_by_date():
    """Test lesson grouping"""
    class MockLesson:
        def __init__(self, day):
            self.day = day
            self.start_time = datetime.min.time()
    
    lessons = [
        MockLesson("monday"),
        MockLesson("wednesday"),
        MockLesson("monday"),
    ]
    
    grouped = group_lessons_by_date(lessons)
    assert len(grouped) == 2  # Two different dates
    # Each date should have correct lessons
```

## Performance Testing

```python
import time
from app.services.date_utils import day_name_to_next_date, format_date_with_day

# Test performance with many day conversions
start = time.time()
for i in range(1000):
    for day in ["monday", "tuesday", "wednesday", "thursday", "friday"]:
        d = day_name_to_next_date(day)
        formatted = format_date_with_day(d)
end = time.time()

print(f"1000 iterations in {end - start:.4f} seconds")
# Should be much less than 1 second
```

## Debugging Tips

1. **Check timezone configuration**: Verify `.env` has `TIMEZONE=Asia/Tashkent`
2. **Enable debug logging**: Add logging to date_utils.py to track calculations
3. **Mock the time**: Use freezegun or similar to test specific dates
4. **Verify imports**: Run Python import tests first before running bot
5. **Check database**: Ensure mock timetable data has populated lessons

## Known Limitations & Notes

- Date calculations ignore daylight saving time transitions (pytz handles this)
- Weekly view calculates dates from current date, not a fixed week start
- Custom day selection returns next occurrence (today if it's that day)
- All times are localized to configured timezone
