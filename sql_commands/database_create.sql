CREATE TABLE IF NOT EXISTS discord_user (
  user_id BIGINT NOT NULL,
  text_length INTEGER NOT NULL,
  created_at BIGINT NOT NULL,
  audio_id VARCHAR(35) NOT NULL
);

CREATE TABLE IF NOT EXISTS files (
  text_input TEXT NOT NULL,
  audio_id VARCHAR(35) NOT NULL,
  created_at BIGINT NOT NULL,
  user_id BIGINT NOT NULL
);
