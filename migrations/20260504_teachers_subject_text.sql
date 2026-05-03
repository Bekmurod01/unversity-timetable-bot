-- Expand teachers.subject to prevent EduPage sync truncation failures.
-- Keeps existing data intact.
ALTER TABLE teachers
    ALTER COLUMN subject TYPE TEXT;
