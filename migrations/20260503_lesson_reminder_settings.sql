ALTER TABLE users ADD COLUMN IF NOT EXISTS lesson_reminder_enabled BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS lesson_reminder_minutes INTEGER NOT NULL DEFAULT 5;

CREATE TABLE IF NOT EXISTS lesson_reminder_dispatches (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    group_name VARCHAR(40) NOT NULL,
    day DATE NOT NULL,
    start_time TIME NOT NULL,
    reminder_minutes INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_reminder_dispatch UNIQUE (user_id, group_name, day, start_time, reminder_minutes)
);

CREATE INDEX IF NOT EXISTS idx_lesson_reminder_dispatch_user ON lesson_reminder_dispatches(user_id);
