from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime

class ScanStartRequest(BaseModel):
    brand_name: str
    website_url: Optional[str] = None
    industry: Optional[str] = None
    run_all_providers: bool = True

class ProviderSummary(BaseModel):
    provider: str
    score: float
    mentions: int
    total: int

class ScanStartResponse(BaseModel):
    scan_job_id: UUID
    status: str
    score: float
    total_prompts_run: int
    brand_mentioned_count: int  
    total_cost_usd: float
    results_summary: List[ProviderSummary]

class FullScanResult(BaseModel):
    prompt_text: str
    provider: str
    brand_mentioned: bool
    response_snippet: str  # first 200 chars only
    cost_usd: float
    latency_ms: int

class ScanJob(BaseModel):
    id: UUID
    brand_id: UUID
    status: str
    total_prompts: int
    completed_prompts: int
    visibility_score: Optional[float] = None
    total_cost_usd: float
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True
    }

# DONE - scan.py
