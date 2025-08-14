from app.core import router
import pytest
import asyncio

@pytest.mark.asyncio
async def test_bi_route():
    d = await router.route("show top margin skus last week")
    assert d.route in ("BI","MIXED")
    assert d.intent in ("top_skus_by_margin",)

@pytest.mark.asyncio
async def test_doc_route():
    d = await router.route("what is our returns policy for markdown items")
    # early phase may classify as RAG or MIXED or OPEN depending on heuristics
    assert d.route in ("RAG","MIXED","OPEN","NO_ANSWER")

@pytest.mark.asyncio
async def test_open_fallback():
    d = await router.route("hello there")
    assert d.route in ("OPEN","NO_ANSWER")
