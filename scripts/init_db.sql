-- Run Alembic migrations instead of this file in production.
-- This is a reference schema for documentation purposes.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'user',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    key TEXT UNIQUE NOT NULL,
    name VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE mt5_accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    broker_name VARCHAR(255),
    account_number VARCHAR(100),
    server_name VARCHAR(255),
    leverage INTEGER,
    account_balance NUMERIC(12,2),
    account_equity NUMERIC(12,2),
    risk_profile VARCHAR(50) DEFAULT 'balanced',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_mt5_user ON mt5_accounts(user_id);

CREATE TABLE ai_signals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    direction VARCHAR(10) NOT NULL,
    probability NUMERIC(5,4) NOT NULL,
    expected_move_pips NUMERIC(6,2),
    regime VARCHAR(50),
    spread NUMERIC(6,2),
    atr NUMERIC(6,5),
    session VARCHAR(50),
    entry_price NUMERIC(12,6),
    stop_loss NUMERIC(12,6),
    take_profit NUMERIC(12,6),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE trades (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    account_id UUID REFERENCES mt5_accounts(id) ON DELETE CASCADE NOT NULL,
    signal_id UUID REFERENCES ai_signals(id) ON DELETE SET NULL,
    mt5_ticket BIGINT,
    symbol VARCHAR(20) NOT NULL,
    direction VARCHAR(10) NOT NULL,
    lot_size NUMERIC(10,4) NOT NULL,
    entry_price NUMERIC(12,6),
    stop_loss NUMERIC(12,6),
    take_profit NUMERIC(12,6),
    exit_price NUMERIC(12,6),
    profit_loss NUMERIC(12,2),
    status VARCHAR(20) DEFAULT 'open',
    opened_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_trades_account ON trades(account_id);
CREATE INDEX idx_trades_opened ON trades(opened_at);

CREATE TABLE risk_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    account_id UUID REFERENCES mt5_accounts(id) ON DELETE CASCADE NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    description TEXT,
    triggered_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE daily_performance (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    account_id UUID REFERENCES mt5_accounts(id) ON DELETE CASCADE NOT NULL,
    date DATE NOT NULL,
    starting_balance NUMERIC(12,2) NOT NULL,
    ending_balance NUMERIC(12,2) NOT NULL,
    daily_return_percent NUMERIC(6,3) DEFAULT 0,
    max_drawdown_percent NUMERIC(6,3) DEFAULT 0,
    total_trades INTEGER DEFAULT 0,
    UNIQUE(account_id, date)
);

CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    plan_name VARCHAR(100) NOT NULL,
    price NUMERIC(10,2) NOT NULL,
    billing_cycle VARCHAR(20) DEFAULT 'monthly',
    status VARCHAR(50) DEFAULT 'pending',
    started_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    amount NUMERIC(10,2) NOT NULL,
    payment_provider VARCHAR(50) DEFAULT 'paystack',
    provider_transaction_id VARCHAR(255) UNIQUE,
    status VARCHAR(50) DEFAULT 'pending',
    plan_name VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
