-- BudgetOps AI Database Schema
-- Run this in your Supabase SQL Editor

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table (for future multi-user support)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    gmail_connected BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Transactions table
CREATE TABLE IF NOT EXISTS transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    
    -- Transaction details
    amount DECIMAL(12, 2) NOT NULL,
    transaction_type VARCHAR(10) NOT NULL CHECK (transaction_type IN ('credit', 'debit')),
    card VARCHAR(255),
    to_merchant VARCHAR(255),
    transaction_reference_number VARCHAR(100),
    description TEXT,
    
    -- Dates
    transaction_date DATE NOT NULL,
    transaction_timestamp TIMESTAMP WITH TIME ZONE,
    
    -- Email metadata
    email_id VARCHAR(255) UNIQUE,
    email_subject TEXT,
    email_date VARCHAR(255),
    
    -- AI-generated fields (added later)
    category VARCHAR(50),
    ai_insight TEXT,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Budgets table (for future budget tracking)
CREATE TABLE IF NOT EXISTS budgets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    
    category VARCHAR(50) NOT NULL,
    monthly_limit DECIMAL(12, 2) NOT NULL,
    current_spent DECIMAL(12, 2) DEFAULT 0,
    
    month INTEGER NOT NULL,
    year INTEGER NOT NULL,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(user_id, category, month, year)
);

-- Daily insights table
CREATE TABLE IF NOT EXISTS daily_insights (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    
    insight_date DATE NOT NULL,
    total_spent DECIMAL(12, 2) NOT NULL,
    total_earned DECIMAL(12, 2) NOT NULL,
    transaction_count INTEGER NOT NULL,
    
    ai_summary TEXT,
    ai_recommendations TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(user_id, insight_date)
);

-- Indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(transaction_date);
CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(transaction_type);
CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category);
CREATE INDEX IF NOT EXISTS idx_transactions_email_id ON transactions(email_id);

CREATE INDEX IF NOT EXISTS idx_budgets_user_id ON budgets(user_id);
CREATE INDEX IF NOT EXISTS idx_budgets_month_year ON budgets(month, year);

CREATE INDEX IF NOT EXISTS idx_insights_user_id ON daily_insights(user_id);
CREATE INDEX IF NOT EXISTS idx_insights_date ON daily_insights(insight_date);

-- Update timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_transactions_updated_at
    BEFORE UPDATE ON transactions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_budgets_updated_at
    BEFORE UPDATE ON budgets
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Insert default user for development (optional)
-- Replace with your email
INSERT INTO users (email, gmail_connected) 
VALUES ('your_email@example.com', TRUE)
ON CONFLICT (email) DO NOTHING;

-- Grant permissions (if using RLS)
-- ALTER TABLE users ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE budgets ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE daily_insights ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE transactions IS 'Stores parsed transaction data from email alerts';
COMMENT ON TABLE budgets IS 'User-defined monthly budgets by category';
COMMENT ON TABLE daily_insights IS 'AI-generated daily spending insights';