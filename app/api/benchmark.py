import logging
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from typing import Dict, Any

from app.auth.middleware import get_current_user
from app.benchmark.corpus import get_industry_benchmark, recompute_benchmark_corpus
from app.benchmark.comparisons import compare_brand_with_industry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/benchmark", tags=["Benchmark Corpus"])

class BenchmarkResponse(BaseModel):
    brand_score: float
    industry: str
    percentile: int
    message: str
    industry_avg: float
    industry_p75: float
    industry_p90: float
    peer_comparison: str

@router.get("/{brand_id}", response_model=BenchmarkResponse)
async def get_brand_benchmark(brand_id: str):
    """
    Returns benchmark ranking, percentile, industry stats, and peer comparison for a brand.
    """
    try:
        data = await compare_brand_with_industry(brand_id)
        return BenchmarkResponse(
            brand_score=data["brand_score"],
            industry=data["industry"],
            percentile=data["percentile"],
            message=data["message"],
            industry_avg=data["industry_avg"],
            industry_p75=data["industry_p75"],
            industry_p90=data["industry_p90"],
            peer_comparison=data["peer_comparison"]
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        logger.error(f"Error fetching benchmark for brand {brand_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch benchmark")

@router.get("/industry/{industry}")
async def get_industry_benchmark_stats(industry: str):
    """
    Returns benchmark stats (avg, p25, p50, p75, p90, brand_count) for a specified industry.
    """
    try:
        data = await get_industry_benchmark(industry)
        return data
    except Exception as e:
        logger.error(f"Error fetching benchmark for industry {industry}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch industry benchmark")

@router.post("/recompute")
async def recompute_benchmarks(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Triggers manual recomputation of benchmark corpus per industry.
    Requires authenticated user (admin/analyst).
    """
    try:
        result = await recompute_benchmark_corpus()
        return result
    except Exception as e:
        logger.error(f"Error recomputing benchmarks: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to recompute benchmarks")
