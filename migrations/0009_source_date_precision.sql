ALTER TABLE source_date_assertions
ADD COLUMN date_precision TEXT NOT NULL DEFAULT 'instant'
CHECK (date_precision IN ('instant', 'calendar_day'));
