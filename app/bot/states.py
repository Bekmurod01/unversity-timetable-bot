from aiogram.fsm.state import State, StatesGroup


class RegistrationFSM(StatesGroup):
    full_name = State()
    faculty = State()
    year = State()
    group_name = State()
    confirmation = State()


class RoomFinderFSM(StatesGroup):
    waiting_room = State()


class TeacherSearchFSM(StatesGroup):
    waiting_name = State()


class SettingsFSM(StatesGroup):
    waiting_name = State()
    waiting_group = State()
    waiting_faculty = State()
    waiting_year = State()
