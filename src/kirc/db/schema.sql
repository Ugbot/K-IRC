-- K-IRC PostgreSQL Schema
-- Stores service credentials, user profiles, contacts, and message history

-- Service configurations (Kafka, PostgreSQL, Valkey credentials)
CREATE TABLE IF NOT EXISTS service_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_type VARCHAR(50) NOT NULL,  -- kafka, postgresql, valkey
    name VARCHAR(255) NOT NULL,
    host VARCHAR(255) NOT NULL,
    port INTEGER NOT NULL,
    username VARCHAR(255),
    password VARCHAR(255),
    ssl_enabled BOOLEAN DEFAULT TRUE,
    ssl_ca_cert TEXT,
    ssl_client_cert TEXT,
    ssl_client_key TEXT,
    extra_config JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_service_configs_type ON service_configs(service_type);

-- User profile (local user configuration)
CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(255) UNIQUE NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    public_key TEXT,
    avatar_url TEXT,
    status VARCHAR(50) DEFAULT 'online',
    bio TEXT,
    is_public BOOLEAN DEFAULT TRUE,
    quota_bytes_per_day INTEGER DEFAULT 1048576,  -- 1MB default
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Contacts (peers we communicate with)
CREATE TABLE IF NOT EXISTS contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(255) UNIQUE NOT NULL,
    display_name VARCHAR(255),
    kafka_bootstrap_servers VARCHAR(512) NOT NULL,
    public_key TEXT,
    notes TEXT,
    is_blocked BOOLEAN DEFAULT FALSE,
    last_seen TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_contacts_username ON contacts(username);
CREATE INDEX idx_contacts_blocked ON contacts(is_blocked);

-- Message history (long-term storage)
CREATE TABLE IF NOT EXISTS messages (
    id BIGINT PRIMARY KEY,
    message_type VARCHAR(50) NOT NULL,  -- chat, direct, broadcast, etc.
    sender VARCHAR(255) NOT NULL,
    recipient VARCHAR(255),
    channel VARCHAR(255),
    content BYTEA NOT NULL,  -- msgpack-encoded content
    timestamp TIMESTAMPTZ NOT NULL,
    is_outbound BOOLEAN NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_messages_sender ON messages(sender);
CREATE INDEX idx_messages_recipient ON messages(recipient);
CREATE INDEX idx_messages_channel ON messages(channel);
CREATE INDEX idx_messages_timestamp ON messages(timestamp DESC);
CREATE INDEX idx_messages_unread ON messages(is_read) WHERE is_read = FALSE;

-- Trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER service_configs_updated_at
    BEFORE UPDATE ON service_configs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER user_profiles_updated_at
    BEFORE UPDATE ON user_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER contacts_updated_at
    BEFORE UPDATE ON contacts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
