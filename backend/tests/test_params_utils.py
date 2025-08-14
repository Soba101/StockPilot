from app.core import params

def test_normalize_time_today():
    start, end = params.normalize_time("today show me stuff")
    assert start <= end

def test_parse_numbers_units():
    meta = params.parse_numbers_units("markdown slow movers by 20% in 30 days reorder 50 units")
    assert meta.get('percent') == 0.2
    assert meta.get('days') == 30 or meta.get('qty') == 50

def test_resolve_skus():
    skus = params.resolve_skus("how many iphone and macbook items")
    assert 'APPL-IPH-001' in skus
