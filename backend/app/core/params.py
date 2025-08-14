"""Natural language parameter extraction utilities (SGT aware)."""
from __future__ import annotations
from typing import Tuple, List, Dict, Any
from datetime import datetime, timedelta
import re
import zoneinfo
from app.core.config import settings

SGT = zoneinfo.ZoneInfo(settings.APP_TZ)

RELATIVE_PATTERNS = [
    (re.compile(r"today", re.I), lambda now: (now.replace(hour=0, minute=0, second=0, microsecond=0), now)),
    (re.compile(r"yesterday", re.I), lambda now: ( (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0), (now - timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=0))),
    (re.compile(r"last week|past week", re.I), lambda now: ( (now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0), now)),
    (re.compile(r"last (?:30|thirty) days|past 30 days", re.I), lambda now: ( (now - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0), now)),
    (re.compile(r"this month", re.I), lambda now: ( now.replace(day=1, hour=0, minute=0, second=0, microsecond=0), now)),
]

QUARTER_PATTERN = re.compile(r"q([1-4])", re.I)


def normalize_time(nl_text: str, tz: str = settings.APP_TZ) -> Tuple[str, str]:
    now = datetime.now(SGT)
    for pattern, fn in RELATIVE_PATTERNS:
        if pattern.search(nl_text):
            start, end = fn(now)
            return start.isoformat(), end.isoformat()
    # Quarter detection (calendar; fiscal handled separately later if needed)
    qm = QUARTER_PATTERN.search(nl_text)
    if qm:
        q = int(qm.group(1))
        year = now.year
        start_month = (q - 1) * 3 + 1
        start = datetime(year, start_month, 1, tzinfo=SGT)
        if start_month + 3 > 12:
            end = datetime(year+1, 1, 1, tzinfo=SGT) - timedelta(seconds=1)
        else:
            end = datetime(year, start_month + 3, 1, tzinfo=SGT) - timedelta(seconds=1)
        return start.isoformat(), end.isoformat()
    # Default: last 7 days
    return (now - timedelta(days=7)).isoformat(), now.isoformat()

NUMBER_UNIT_PATTERN = re.compile(r"(?P<num>\d+(?:\.\d+)?)\s?(?P<unit>%|percent|pcs|units|days?)", re.I)

def parse_numbers_units(nl_text: str) -> Dict[str, Any]:
    results: Dict[str, Any] = {}
    for m in NUMBER_UNIT_PATTERN.finditer(nl_text):
        num = float(m.group('num'))
        unit = m.group('unit').lower()
        if unit in ('%', 'percent'):
            results['percent'] = num / 100.0
        elif unit.startswith('day'):
            results['days'] = int(num)
        else:
            results['qty'] = int(num)
    return results

# Placeholder alias map (in future load from JSON / DB)
ALIAS_MAP = {
    'iphone': ['APPL-IPH-001'],
    'macbook': ['APPL-MBP-001', 'APPL-MBA-001']
}

ALIAS_PATTERN = re.compile('|'.join(re.escape(k) for k in ALIAS_MAP.keys()), re.I)

def resolve_skus(nl_text: str) -> List[str]:
    skus: List[str] = []
    for m in ALIAS_PATTERN.finditer(nl_text):
        key = m.group(0).lower()
        skus.extend(ALIAS_MAP.get(key, []))
    return list(dict.fromkeys(skus))  # dedupe preserve order
