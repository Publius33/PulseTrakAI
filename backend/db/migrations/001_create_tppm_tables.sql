-- Migration: Create TPPM tables for PulseTrakAI
-- © PUBLIUS33™ — PulseTrakAI™. All Rights Reserved.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS metric_events (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  source TEXT,
  metric TEXT,
  value DOUBLE PRECISION,
  timestamp TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS temporal_baselines (
  metric TEXT,
  hour_of_day INT,
  day_of_week INT,
  expected_value DOUBLE PRECISION,
  std_dev DOUBLE PRECISION,
  PRIMARY KEY (metric, hour_of_day, day_of_week)
);

CREATE TABLE IF NOT EXISTS pulse_predictions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  generated_at TIMESTAMPTZ DEFAULT now(),
  horizon_hours INT,
  probability DOUBLE PRECISION,
  explanation TEXT
);

CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email TEXT UNIQUE,
  stripe_customer_id TEXT,
  api_key TEXT
);
