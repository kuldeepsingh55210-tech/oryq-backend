"""
PostgreSQL Schema (Supabase) Database Configurations

CREATE TABLE brands (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    website_url TEXT,
    industry TEXT,
    aliases TEXT[],
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE scan_jobs (
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

CREATE TABLE scan_results (
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

CREATE TABLE prompts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_id UUID REFERENCES brands(id),
    text TEXT NOT NULL,
    category TEXT,  -- discovery|comparison|evaluation|recommendation
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE llm_cost_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_job_id UUID REFERENCES scan_jobs(id),
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    tokens_in INTEGER,
    tokens_out INTEGER,
    cost_usd NUMERIC(10,8),
    created_at TIMESTAMPTZ DEFAULT now()
);
"""

import os
import logging
from supabase import create_client, Client
from app.config import settings

logger = logging.getLogger(__name__)

_supabase_client: Client = None

def get_supabase_client() -> Client:
    """
    Returns the singleton instance of the sync Supabase client.
    Initializes on demand to allow configuration to load first.
    Defensively strips whitespace from URL and key to prevent 'Invalid URL' errors.
    """
    global _supabase_client
    if _supabase_client is None:
        url = settings.SUPABASE_URL.strip()
        key = settings.SUPABASE_KEY.strip()

        # Debug diagnostics — logged once on first client creation
        logger.info(f"DEBUG Supabase URL: '{url}'")
        logger.info(f"DEBUG Supabase KEY length: {len(key)}")
        logger.info(f"DEBUG os.getenv SUPABASE_URL: '{os.getenv('SUPABASE_URL', '')}'")
        logger.info(f"DEBUG os.getenv SUPABASE_KEY length: {len(os.getenv('SUPABASE_KEY', ''))}")

        if not url or not key:
            logger.warning("Supabase URL or Key is not configured. Database operations will fail.")

        _supabase_client = create_client(url, key)
    return _supabase_client

# DONE - database.py
