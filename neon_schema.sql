-- Part B: Schema for "contextual meaning"
-- Run this against your Neon PostgreSQL database.
--
-- Numeric convention: a leading minus means negative (e.g. -3 is essentially saying negative 3).

-- =============================================================================
-- Table: forecast_metrics
-- Stores Year, Inflation_pct, OFR_change per country + optional contextual meaning
-- =============================================================================
CREATE TABLE IF NOT EXISTS forecast_metrics (
  id             SERIAL PRIMARY KEY,
  country        TEXT NOT NULL,
  year           INT  NOT NULL,
  ofr_change     NUMERIC(12, 6),
  inflation_pct  NUMERIC(12, 6),
  context_meaning TEXT,
  horizon        TEXT NOT NULL,
  created_at     TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(country, year, horizon)
);

COMMENT ON TABLE forecast_metrics IS 'Per-country, per-year forecast of overfishing and inflation metrics. horizon is 5y or 10y (risk_score_5y / risk_score_10y refer to risk over next 5 or 10 years).';
COMMENT ON COLUMN forecast_metrics.ofr_change IS 'Percentage increase/decrease of overfishing within the current year compared to previous years. A leading minus means negative (e.g. -3 is essentially saying negative 3). Negative = decrease, positive = increase, 0 = no change.';
COMMENT ON COLUMN forecast_metrics.inflation_pct IS 'Percentage change of inflation price of fish (current year vs previous years). A leading minus means negative (e.g. -3 is essentially saying negative 3). Negative = decrease, positive = increase, 0 = no change.';
COMMENT ON COLUMN forecast_metrics.horizon IS '5y = risk/forecast for next 5 years, 10y = next 10 years.';
COMMENT ON COLUMN forecast_metrics.context_meaning IS 'Optional free-text explanation of what the numbers mean in context (e.g. "Next 5-year forecast; low pressure").';

-- =============================================================================
-- Table: risk_score_intervals
-- Bands (low/medium/high) and their contextual meaning
-- risk_score_5y = risk score for next 5 years, risk_score_10y = next 10 years
-- Low: 0.00–0.45, Medium: 0.45–0.55, High: 0.55–1.0
-- =============================================================================
CREATE TABLE IF NOT EXISTS risk_score_intervals (
  id             SERIAL PRIMARY KEY,
  band_name      TEXT NOT NULL UNIQUE,
  min_score      NUMERIC(4, 2) NOT NULL,
  max_score      NUMERIC(4, 2) NOT NULL,
  context_meaning TEXT NOT NULL,
  sort_order     INT DEFAULT 0,
  created_at     TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO risk_score_intervals (band_name, min_score, max_score, context_meaning, sort_order)
VALUES
  ('low',   0.00, 0.45, 'Low risk: risk score 0.00 to 0.45 for next 5y or 10y.', 1),
  ('medium', 0.45, 0.55, 'Medium risk: risk score 0.45 to 0.55 for next 5y or 10y.', 2),
  ('high',  0.55, 1.00, 'High risk: risk score 0.55 to 1.0 for next 5y or 10y.', 3)
ON CONFLICT (band_name) DO UPDATE SET
  min_score = EXCLUDED.min_score,
  max_score = EXCLUDED.max_score,
  context_meaning = EXCLUDED.context_meaning,
  sort_order = EXCLUDED.sort_order;

COMMENT ON TABLE risk_score_intervals IS 'Risk score bands: low (0–0.45), medium (0.45–0.55), high (0.55–1.0). risk_score_5y = risk for next 5 years, risk_score_10y = next 10 years.';

-- =============================================================================
-- Step 5: Per-country risk category
-- One row per country: risk scores and predicted band for 5y and 10y
-- =============================================================================
CREATE TABLE IF NOT EXISTS country_risk_category (
  id             SERIAL PRIMARY KEY,
  country        TEXT NOT NULL UNIQUE,
  risk_score_5y  NUMERIC(6, 4),
  risk_score_10y NUMERIC(6, 4),
  risk_5y        TEXT NOT NULL,
  risk_10y       TEXT NOT NULL,
  context_meaning TEXT,
  updated_at     TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE country_risk_category IS 'Per-country risk category: risk_score_5y/10y (0–1), risk_5y/risk_10y = low|medium|high. Bands: low 0–0.45, medium 0.45–0.55, high 0.55–1.0.';
COMMENT ON COLUMN country_risk_category.risk_5y IS 'Risk category for next 5 years: low, medium, or high.';
COMMENT ON COLUMN country_risk_category.risk_10y IS 'Risk category for next 10 years: low, medium, or high.';
COMMENT ON COLUMN country_risk_category.context_meaning IS 'Optional free-text interpretation for this country (e.g. for RAG).';
