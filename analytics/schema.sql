-- Daily aggregate counters only. No individual-event log or visitor identifier.
CREATE TABLE IF NOT EXISTS event_counts (
  day TEXT NOT NULL,
  event TEXT NOT NULL CHECK (event IN (
    'page_home','page_search','page_copy','nav_search',
    'nav_copy','copy_field','copy_all','session_start'
  )),
  count INTEGER NOT NULL DEFAULT 0 CHECK (count >= 0),
  PRIMARY KEY (day, event)
);
