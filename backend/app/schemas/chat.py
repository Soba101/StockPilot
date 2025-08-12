from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field, validator

# Intent parameter models

PeriodEnum = Literal['7d','30d']

class TopSkusByMarginParams(BaseModel):
    period: PeriodEnum = '7d'
    n: int = Field(10, ge=1, le=50)
    channel: Optional[str] = None
    location_id: Optional[str] = Field(None, alias='location')

class StockoutRiskParams(BaseModel):
    horizon_days: int = Field(14, ge=7, le=30)
    location_id: Optional[str] = Field(None, alias='location')

class WeekInReviewParams(BaseModel):
    location_id: Optional[str] = Field(None, alias='location')
    channel: Optional[str] = None

class ReorderSuggestionsParams(BaseModel):
    location_id: Optional[str] = Field(None, alias='location')

class SlowMoversParams(BaseModel):
    period: PeriodEnum = '30d'
    n: int = Field(10, ge=1, le=50)

class ProductDetailParams(BaseModel):
    sku: Optional[str] = None
    name: Optional[str] = None

IntentName = Literal['top_skus_by_margin','stockout_risk','week_in_review','reorder_suggestions','slow_movers','product_detail']

# Chat request / response
class ChatQueryRequest(BaseModel):
    prompt: str
    intent: Optional[IntentName] = Field(None, description="Optional explicit intent override (advanced)")
    # raw params; will be validated against chosen intent schema
    params: Dict[str, Any] = Field(default_factory=dict)

class DataColumn(BaseModel):
    name: str
    type: str
    label: Optional[str] = None

class QueryExplainer(BaseModel):
    definition: str
    sql: Optional[str] = None
    sources: List[Dict[str, Any]] = []

class FreshnessMeta(BaseModel):
    generated_at: str
    data_fresh_at: Optional[str] = None
    max_lag_seconds: Optional[int] = None

class ConfidenceMeta(BaseModel):
    level: Literal['high','medium','low']
    reasons: List[str] = []

class NextAction(BaseModel):
    label: str
    action_type: str
    payload: Dict[str, Any]

class ChatQueryResponse(BaseModel):
    intent: Optional[IntentName]  # Allow None for general chat
    title: str
    answer_summary: str
    data: Dict[str, Any]
    query_explainer: QueryExplainer
    freshness: FreshnessMeta
    confidence: ConfidenceMeta
    next_action: Optional[NextAction] = None
    warnings: List[str] = []
    source: Literal['rules','llm'] = 'rules'

class IntentResolution(BaseModel):
    intent: Optional[IntentName]
    params: Dict[str, Any] = {}
    confidence: float = 0.0
    source: Literal['rules','llm'] = 'rules'
    reasons: List[str] = []

    @property
    def ok(self) -> bool:
        return self.intent is not None and self.confidence >= 0.5
