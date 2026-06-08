-- 006_email_verification_tokens.sql
-- 2026-06-08 bpietrzakk
--
-- Email verification: short-lived single-use tokens emailed after register.
-- Same shape as password_reset_tokens — token_hash stores a hash of the
-- token, never the raw value. used_at is set when consumed (NULL = unused).
-- Clicking the link flips users.email_verified to TRUE.

CREATE TABLE email_verification_tokens (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash  TEXT        NOT NULL,
    expires_at  TIMESTAMPTZ NOT NULL,
    used_at     TIMESTAMPTZ
);

CREATE INDEX idx_email_verification_tokens_token_hash ON email_verification_tokens(token_hash);
CREATE INDEX idx_email_verification_tokens_expires_at ON email_verification_tokens(expires_at);
