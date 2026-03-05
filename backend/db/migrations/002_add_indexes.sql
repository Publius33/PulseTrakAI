-- Database Migration: Add Indexes for Performance
-- Migration ID: 002_add_indexes
-- Description: Add indexes to frequently queried columns

-- © PUBLIUS33™ — PulseTrakAI™ — All Rights Reserved.

-- Metric events indexes
CREATE INDEX IF NOT EXISTS idx_metric_events_timestamp 
  ON metric_events(timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_metric_events_source 
  ON metric_events(source);

CREATE INDEX IF NOT EXISTS idx_metric_events_metric_source 
  ON metric_events(metric, source);

-- Predictions indexes
CREATE INDEX IF NOT EXISTS idx_pulse_predictions_generated_at 
  ON pulse_predictions(generated_at DESC);

CREATE INDEX IF NOT EXISTS idx_pulse_predictions_metric 
  ON pulse_predictions(metric_name);

-- Users indexes
CREATE INDEX IF NOT EXISTS idx_users_email 
  ON users(username);

-- Audit logs indexes
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at 
  ON audit_logs(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id 
  ON audit_logs(user_id);

CREATE INDEX IF NOT EXISTS idx_audit_logs_action 
  ON audit_logs(action);

-- Composite indexes for common queries
CREATE INDEX IF NOT EXISTS idx_metric_events_metric_timestamp 
  ON metric_events(metric, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_predictions_metric_timestamp 
  ON pulse_predictions(metric_name, generated_at DESC);
