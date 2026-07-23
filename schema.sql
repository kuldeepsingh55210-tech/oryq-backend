-- PostgreSQL Database Schema for ORYQ

CREATE TABLE IF NOT EXISTS brands (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    website_url TEXT,
    industry TEXT,
    aliases TEXT[],
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS scan_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_id UUID REFERENCES brands(id),
    status TEXT DEFAULT 'queued',  -- queued|running|completed|failed
    total_prompts INTEGER DEFAULT 0,
    completed_prompts INTEGER DEFAULT 0,
    visibility_score NUMERIC(5,2),
    total_cost_usd NUMERIC(10,8) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS scan_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_job_id UUID REFERENCES scan_jobs(id),
    prompt_text TEXT NOT NULL,
    provider TEXT NOT NULL,  -- groq|gemini|openai
    brand_mentioned BOOLEAN DEFAULT false,
    response_text TEXT,
    cost_usd NUMERIC(10,8) DEFAULT 0,
    latency_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS prompts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_id UUID REFERENCES brands(id),
    text TEXT NOT NULL,
    category TEXT,  -- discovery|comparison|evaluation|recommendation
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS llm_cost_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_job_id UUID REFERENCES scan_jobs(id),
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    tokens_in INTEGER,
    tokens_out INTEGER,
    cost_usd NUMERIC(10,8),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Phase 2: Hallucination Detector
CREATE TABLE IF NOT EXISTS hallucinations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_job_id UUID REFERENCES scan_jobs(id),
    brand_id UUID REFERENCES brands(id),
    claim TEXT NOT NULL,
    source_response TEXT,
    provider TEXT,
    severity TEXT DEFAULT 'medium',
    status TEXT DEFAULT 'unresolved',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Phase 2: Citation Gap Finder
CREATE TABLE IF NOT EXISTS citation_gaps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_job_id UUID REFERENCES scan_jobs(id),
    brand_id UUID REFERENCES brands(id),
    domain TEXT NOT NULL,
    cites_competitor TEXT,
    cites_brand BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Phase 3: Auth System
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    role TEXT DEFAULT 'analyst',
    password_hash TEXT,
    email_verified BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Phase 4: Sentiment Engine V2 & Reputation
CREATE TABLE IF NOT EXISTS sentiment_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_job_id UUID REFERENCES scan_jobs(id) ON DELETE CASCADE,
    scan_result_id UUID REFERENCES scan_results(id) ON DELETE CASCADE,
    sentiment TEXT NOT NULL,  -- positive|negative|neutral
    sentiment_score NUMERIC(4,3),  -- -1.000 to +1.000
    classification_method TEXT NOT NULL,  -- rule_based|llm
    has_hallucination BOOLEAN DEFAULT false,
    hallucination_text TEXT,
    hallucination_status TEXT DEFAULT 'unreviewed', -- unreviewed|confirmed|resolved|false_positive
    risk_level TEXT, -- low|medium|high|critical
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS reputation_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_id UUID REFERENCES brands(id) ON DELETE CASCADE,
    scan_job_id UUID REFERENCES scan_jobs(id) ON DELETE CASCADE,
    reputation_score NUMERIC(5,2),
    positive_pct NUMERIC(5,2),
    negative_pct NUMERIC(5,2),
    neutral_pct NUMERIC(5,2),
    risk_level TEXT, -- low|medium|high|critical
    narrative_summary TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Phase 5: Entity Intelligence System
CREATE TABLE IF NOT EXISTS brand_entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_id UUID REFERENCES brands(id) ON DELETE CASCADE,
    entity_name TEXT NOT NULL,
    entity_type TEXT NOT NULL,  -- product|person|differentiator|technology|award|location
    is_known_to_ai BOOLEAN DEFAULT false,
    coverage_pct NUMERIC(5,2) DEFAULT 0,
    last_seen_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS entity_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_entity_id UUID REFERENCES brand_entities(id) ON DELETE CASCADE,
    target_entity_id UUID REFERENCES brand_entities(id) ON DELETE CASCADE,
    relationship_type TEXT,
    strength NUMERIC(4,3) DEFAULT 0.5,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Phase 6: Prompt Discovery Engine
CREATE TABLE IF NOT EXISTS prompt_suggestions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_id UUID REFERENCES brands(id) ON DELETE CASCADE,
    prompt_text TEXT NOT NULL,
    cluster TEXT,  -- Discovery|Comparison|Evaluation|Recommendation
    estimated_lift_pct NUMERIC(5,2),
    competitor_visibility NUMERIC(5,2),
    status TEXT DEFAULT 'pending',  -- pending|approved|rejected|added
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS prompt_clusters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_id UUID REFERENCES brands(id) ON DELETE CASCADE,
    cluster_name TEXT NOT NULL,  -- Discovery|Comparison|Evaluation|Recommendation
    prompt_count INTEGER DEFAULT 0,
    avg_visibility_pct NUMERIC(5,2),
    gap_score NUMERIC(5,2),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Phase 7: Benchmark Corpus (Module E)
CREATE TABLE IF NOT EXISTS benchmark_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    industry TEXT NOT NULL,
    avg_visibility_score NUMERIC(5,2),
    p25 NUMERIC(5,2),
    p50 NUMERIC(5,2),
    p75 NUMERIC(5,2),
    p90 NUMERIC(5,2),
    brand_count INTEGER DEFAULT 0,
    computed_at TIMESTAMPTZ DEFAULT now()
);

-- Phase 8: Agency Tools (Module F)
CREATE TABLE IF NOT EXISTS workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    plan_tier TEXT DEFAULT 'agency',
    client_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS workspace_brands (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    brand_id UUID REFERENCES brands(id) ON DELETE CASCADE,
    client_name TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(workspace_id, brand_id)
);

CREATE TABLE IF NOT EXISTS whitelabel_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE UNIQUE,
    agency_name TEXT,
    logo_url TEXT,
    primary_color TEXT DEFAULT '#1B4FD8',
    secondary_color TEXT DEFAULT '#0EA47A',
    report_footer TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Phase 9: Advanced Alerts (Module G)
CREATE TABLE IF NOT EXISTS alert_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_id UUID REFERENCES brands(id) ON DELETE CASCADE,
    alert_type TEXT NOT NULL,
    enabled BOOLEAN DEFAULT true,
    threshold_pct NUMERIC(5,2),
    channels TEXT[] DEFAULT '{email}',
    slack_webhook_url TEXT,
    custom_webhook_url TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(brand_id, alert_type)
);

CREATE TABLE IF NOT EXISTS alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_id UUID REFERENCES brands(id) ON DELETE CASCADE,
    alert_type TEXT NOT NULL,
    severity TEXT DEFAULT 'medium',
    title TEXT NOT NULL,
    body TEXT,
    data_json JSONB,
    delivered_at TIMESTAMPTZ,
    dismissed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Phase 10: Revenue Intelligence (Module H)
CREATE TABLE IF NOT EXISTS revenue_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_id UUID REFERENCES brands(id) ON DELETE CASCADE,
    scan_job_id UUID REFERENCES scan_jobs(id) ON DELETE CASCADE,
    estimated_ai_revenue NUMERIC(12,2),
    missed_revenue NUMERIC(12,2),
    competitor_deals_lost INTEGER DEFAULT 0,
    visibility_score NUMERIC(5,2),
    revenue_per_visibility_point NUMERIC(10,2),
    avg_deal_value NUMERIC(10,2) DEFAULT 50000,
    monthly_ai_leads INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS revenue_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_id UUID REFERENCES brands(id) ON DELETE CASCADE UNIQUE,
    avg_deal_value NUMERIC(10,2) DEFAULT 50000,
    monthly_website_traffic INTEGER DEFAULT 10000,
    ai_traffic_percentage NUMERIC(5,2) DEFAULT 15,
    conversion_rate NUMERIC(5,4) DEFAULT 0.02,
    currency TEXT DEFAULT 'INR',
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- DONE - schema.sql




