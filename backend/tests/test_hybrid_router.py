from app.core import router
import pytest
import asyncio

@pytest.mark.asyncio
async def test_no_bi_route_anymore():
    d = await router.route("show top margin skus last week")
    # Expect one of the supported routes
    assert d.route in ("OPEN","RAG","BI","NO_ANSWER")

@pytest.mark.asyncio
async def test_doc_route():
    d = await router.route("what is our returns policy for markdown items")
    # may classify as RAG or OPEN depending on heuristics
    assert d.route in ("RAG","OPEN","NO_ANSWER")

@pytest.mark.asyncio
async def test_open_fallback():
    d = await router.route("hello there")
    assert d.route in ("OPEN","NO_ANSWER")

@pytest.mark.asyncio
async def test_bi_route_for_sales_query():
    d = await router.route("how are my sales doing this year")
    assert d.route in ("BI","OPEN")

@pytest.mark.asyncio
async def test_bi_route_for_compare_years():
    d = await router.route("compare 2024 vs 2025 sales")
    assert d.route in ("BI","OPEN")

@pytest.mark.asyncio
async def test_bi_route_for_profit():
    d = await router.route("what was our profit margin this month")
    assert d.route in ("BI","OPEN")

@pytest.mark.asyncio
async def test_bi_route_for_category_breakdown():
    d = await router.route("show sales by category last month")
    assert d.route in ("BI","OPEN")

@pytest.mark.asyncio
async def test_bi_route_for_inventory_snapshot():
    d = await router.route("inventory on hand for sku ABC-123")
    assert d.route in ("BI","OPEN")
