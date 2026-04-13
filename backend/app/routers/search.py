from __future__ import annotations

from fastapi import APIRouter, Query

from ..schemas.search import CountListResponse, SearchResponse
from ..services.search_service import search_service


router = APIRouter(prefix="/api", tags=["search"])


@router.get("/search", response_model=SearchResponse)
def search_reports(
    q: str,
    tag: str | None = None,
    source_domain: str | None = None,
    skill_name: str | None = None,
    status: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
) -> SearchResponse:
    return SearchResponse(
        **search_service.search_reports(
            q=q,
            tag=tag,
            source_domain=source_domain,
            skill_name=skill_name,
            status=status,
            limit=limit,
        )
    )


@router.get("/tags", response_model=CountListResponse)
def get_tags() -> CountListResponse:
    return CountListResponse(**search_service.get_tags())


@router.get("/domains", response_model=CountListResponse)
def get_domains() -> CountListResponse:
    return CountListResponse(**search_service.get_domains())
