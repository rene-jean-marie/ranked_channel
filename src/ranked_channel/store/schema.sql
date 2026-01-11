PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS videos (
  video_id TEXT PRIMARY KEY,
  url TEXT NOT NULL,
  title TEXT,
  tags_json TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS edges (
  from_video_id TEXT NOT NULL,
  to_video_id TEXT NOT NULL,
  weight INTEGER NOT NULL,
  PRIMARY KEY (from_video_id, to_video_id)
);

CREATE TABLE IF NOT EXISTS video_seen (
  video_id TEXT PRIMARY KEY,
  seen_count INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
  session_id TEXT PRIMARY KEY,
  seed_url TEXT NOT NULL,
  created_at TEXT NOT NULL,
  config_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS session_items (
  session_id TEXT NOT NULL,
  idx INTEGER NOT NULL,
  video_id TEXT NOT NULL,
  url TEXT NOT NULL,
  title TEXT,
  explain_json TEXT NOT NULL,
  PRIMARY KEY (session_id, idx)
);

CREATE TABLE IF NOT EXISTS feedback (
  session_id TEXT NOT NULL,
  video_id TEXT NOT NULL,
  action TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS taste_profile (
  tag TEXT PRIMARY KEY,
  weight REAL NOT NULL
);
