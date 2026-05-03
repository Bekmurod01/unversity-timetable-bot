-- Expand teachers.subject to prevent EduPage sync truncation failures.
-- Keeps existing data intact.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'teachers'
          AND column_name = 'subject'
    ) THEN
        ALTER TABLE teachers
            ALTER COLUMN subject TYPE TEXT;
    END IF;
END $$;
