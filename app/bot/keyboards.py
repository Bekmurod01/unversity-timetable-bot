from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


DEFAULT_FACULTIES = ["IT", "Business", "Finance", "ACCA"]


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📅 My Timetable"), KeyboardButton(text="👨‍🏫 Teacher Timetable")],
            [KeyboardButton(text="🏫 Room Finder"), KeyboardButton(text="🔔 Notifications")],
            [KeyboardButton(text="⭐ Favorites"), KeyboardButton(text="⚙️ Settings")],
            [KeyboardButton(text="ℹ️ Help"), KeyboardButton(text="📢 Announcements")],
        ],
        resize_keyboard=True,
    )


def faculty_keyboard(faculties: list[str] | None = None, prefix: str = "reg_faculty") -> InlineKeyboardMarkup:
    options = faculties or DEFAULT_FACULTIES
    buttons = [[InlineKeyboardButton(text=x, callback_data=f"{prefix}:{x}")] for x in options]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def group_selection_keyboard(
    groups: list[str],
    faculty: str,
    page: int = 1,
    total: int = 0,
    page_size: int = 20,
    callback_prefix: str = "reg_group_page",
    select_prefix: str = "reg_group",
) -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for g in groups:
        row.append(InlineKeyboardButton(text=g, callback_data=f"{select_prefix}:{g}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="⬅️ Previous", callback_data=f"{callback_prefix}:{faculty}:{page-1}"))
    if total > page * page_size:
        nav.append(InlineKeyboardButton(text="Next ➡️", callback_data=f"{callback_prefix}:{faculty}:{page+1}"))

    if nav:
        buttons.append(nav)

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def year_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=str(i))] for i in range(1, 6)],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def yes_no_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="✅ Confirm"), KeyboardButton(text="✏️ Edit")]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def timetable_mode_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Today"), KeyboardButton(text="Tomorrow")],
            [KeyboardButton(text="Weekly"), KeyboardButton(text="Custom Day")],
            [KeyboardButton(text="⬅️ Back"), KeyboardButton(text="🏠 Main Menu")],
        ],
        resize_keyboard=True,
    )


def day_picker_keyboard() -> ReplyKeyboardMarkup:
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=day)] for day in days] + [[KeyboardButton(text="⬅️ Back"), KeyboardButton(text="🏠 Main Menu")]],
        resize_keyboard=True,
    )


def notification_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Toggle ON/OFF")],
            [KeyboardButton(text="Only changes"), KeyboardButton(text="Daily reminders")],
            [KeyboardButton(text="Exam alerts"), KeyboardButton(text="⬅️ Back")],
            [KeyboardButton(text="🏠 Main Menu")],
        ],
        resize_keyboard=True,
    )


def reminder_settings_inline_keyboard(selected_minutes: int | None = None) -> InlineKeyboardMarkup:
    options = [5, 10, 15, 30, 60]
    rows = [[
        InlineKeyboardButton(
            text=f"{'✅ ' if selected_minutes == x else ''}{'1 Hour Before' if x == 60 else f'{x} Minutes Before'}",
            callback_data=f"reminder:set:{x}",
        )
    ] for x in options]
    rows.append([InlineKeyboardButton(text="✏️ Custom Reminder", callback_data="reminder:custom")])
    rows.append([InlineKeyboardButton(text="🔕 Disable Notifications", callback_data="reminder:disable")])
    rows.append([
        InlineKeyboardButton(text="⬅️ Back", callback_data="reminder:back"),
        InlineKeyboardButton(text="🏠 Main Menu", callback_data="reminder:home"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def settings_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Change name"), KeyboardButton(text="Change group")],
            [KeyboardButton(text="Change faculty"), KeyboardButton(text="Change year")],
            [KeyboardButton(text="Change language"), KeyboardButton(text="Reset profile")],
            [KeyboardButton(text="⬅️ Back"), KeyboardButton(text="🏠 Main Menu")],
        ],
        resize_keyboard=True,
    )


def teacher_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔍 Search Teacher"), KeyboardButton(text="📋 All Teachers")],
            [KeyboardButton(text="⭐ Favorite Teachers"), KeyboardButton(text="🕒 Recent Searches")],
            [KeyboardButton(text="⬅️ Back"), KeyboardButton(text="🏠 Main Menu")],
        ],
        resize_keyboard=True,
    )


def teacher_inline_keyboard(teacher_id: int, is_favorite: bool = False, notifications_enabled: bool = False, pinned: bool = False) -> InlineKeyboardMarkup:
    fav_text = "⭐ Remove Favorite" if is_favorite else "⭐ Add Favorite"
    notif_text = "🔔 Disable Updates" if notifications_enabled else "🔔 Enable Updates"
    pin_text = "📍 Unpin Teacher" if pinned else "📌 Pin Teacher"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📅 View Schedule", callback_data=f"teacher_view:{teacher_id}")],
            [
                InlineKeyboardButton(text=fav_text, callback_data=f"teacher_fav:{teacher_id}"),
                InlineKeyboardButton(text=notif_text, callback_data=f"teacher_notif:{teacher_id}")
            ],
            [InlineKeyboardButton(text=pin_text, callback_data=f"teacher_pin:{teacher_id}")],
        ]
    )


def teacher_list_keyboard(
    teachers: list,
    prefix: str = "teacher_card",
    page: int = 1,
    total: int = 0,
    page_size: int = 50,
    callback_prefix: str = "teacher_page"
) -> InlineKeyboardMarkup:
    buttons = []
    for item in teachers:
        if hasattr(item, "teacher"):
            t = item.teacher
            label = f"{'📌 ' if item.pinned else ''}{t.name}"
        else:
            t = item
            label = t.name
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"{prefix}:{t.id}")])

    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Previous", callback_data=f"{callback_prefix}:{page-1}"))

    if total > page * page_size:
        nav_buttons.append(InlineKeyboardButton(text="Next ➡️", callback_data=f"{callback_prefix}:{page+1}"))

    if nav_buttons:
        buttons.append(nav_buttons)

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def teacher_alphabet_keyboard() -> InlineKeyboardMarkup:
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    buttons = []
    row = []
    for char in alphabet:
        row.append(InlineKeyboardButton(text=char, callback_data=f"teacher_letter:{char}"))
        if len(row) == 6:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)
