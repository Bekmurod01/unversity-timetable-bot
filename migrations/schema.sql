CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    full_name VARCHAR(120) NOT NULL,
    faculty VARCHAR(80) NOT NULL,
    group_name VARCHAR(40) NOT NULL,
    year INTEGER NOT NULL,
    language VARCHAR(8) NOT NULL DEFAULT 'en',
    notifications_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    notify_changes_only BOOLEAN NOT NULL DEFAULT FALSE,
    notify_daily_reminders BOOLEAN NOT NULL DEFAULT TRUE,
    notify_exam_alerts BOOLEAN NOT NULL DEFAULT TRUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS teachers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(120) UNIQUE NOT NULL,
    subject VARCHAR(120) NOT NULL
);

CREATE TABLE IF NOT EXISTS timetable_lessons (
    id SERIAL PRIMARY KEY,
    group_name VARCHAR(40) NOT NULL,
    subject VARCHAR(120) NOT NULL,
    teacher VARCHAR(120) NOT NULL,
    room VARCHAR(40) NOT NULL,
    day VARCHAR(16) NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    CONSTRAINT uq_lesson_slot UNIQUE (group_name, day, start_time, subject)
);

CREATE TABLE IF NOT EXISTS exam_deadlines (
    id SERIAL PRIMARY KEY,
    group_name VARCHAR(40) NOT NULL,
    subject VARCHAR(120) NOT NULL,
    title VARCHAR(200) NOT NULL,
    due_date TIMESTAMPTZ NOT NULL,
    type VARCHAR(20) NOT NULL DEFAULT 'exam'
);

CREATE TABLE IF NOT EXISTS updates_log (
    id SERIAL PRIMARY KEY,
    group_name VARCHAR(40) NOT NULL,
    change_type VARCHAR(40) NOT NULL,
    details VARCHAR(500) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS favorite_teachers (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    teacher_name VARCHAR(120) NOT NULL,
    CONSTRAINT uq_user_teacher_favorite UNIQUE (user_id, teacher_name)
);

CREATE INDEX IF NOT EXISTS idx_users_group ON users(group_name);
CREATE INDEX IF NOT EXISTS idx_users_year ON users(year);
CREATE INDEX IF NOT EXISTS idx_timetable_group_day ON timetable_lessons(group_name, day);
CREATE INDEX IF NOT EXISTS idx_timetable_teacher ON timetable_lessons(teacher);
CREATE INDEX IF NOT EXISTS idx_timetable_room ON timetable_lessons(room);
CREATE INDEX IF NOT EXISTS idx_updates_group_time ON updates_log(group_name, created_at DESC);
