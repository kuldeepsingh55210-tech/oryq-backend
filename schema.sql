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

-- DONE - schema.sql
