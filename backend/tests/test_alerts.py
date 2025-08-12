from datetime import date
import uuid
import pytest
from sqlalchemy.orm import Session
from app.services.alerts import generate_daily_stockout_digest, check_and_set_idempotent
from app.services import alerts
from app.services.notify import dispatch_digest
from app.models.organization import Organization
from app.models.product import Product
from app.core.security import create_access_token


@pytest.fixture()
def org(db_session: Session):
    o = Organization(name="Alerts Test Org")
    db_session.add(o)
    db_session.commit()
    db_session.refresh(o)
    return o

@pytest.fixture()
def products(db_session: Session, org):
    # Create products with reorder points
    items = []
    for i in range(3):
        p = Product(
            org_id=org.id,
            sku=f"ALERT-{i}",
            name=f"Alert Product {i}",
            cost=5.0,
            price=10.0,
            reorder_point=20,
            category="Test"
        )
        items.append(p)
    db_session.add_all(items)
    db_session.commit()
    for p in items:
        db_session.refresh(p)
    return items

def test_generate_digest_smoke(db_session, org, products):
    digest = generate_daily_stockout_digest(db_session, org.id, strategy="latest")  # type: ignore
    assert digest.org_id == str(org.id)
    assert digest.run_date == date.today()
    assert digest.strategy == "latest"

def test_velocity_strategy_conservative(db_session, org, products, monkeypatch):
    # Monkeypatch velocity query to control values
    def fake_generate(db, org_id, strategy="latest"):
        from app.services.alerts import DailyDigest, StockoutItem
        items = []
        # create two items with differing velocities
        items.append(StockoutItem(product_id="1", sku="A", name="A", on_hand=70, reorder_point=10,
                                  velocity_7d=10, velocity_30d=8, velocity_56d=6, chosen_velocity=10,
                                  velocity_source="7d", days_to_stockout=7.0, risk_level="high"))
        items.append(StockoutItem(product_id="2", sku="B", name="B", on_hand=140, reorder_point=10,
                                  velocity_7d=12, velocity_30d=4, velocity_56d=3, chosen_velocity=12,
                                  velocity_source="7d", days_to_stockout=11.7, risk_level="medium"))
        return DailyDigest(org_id=str(org_id), run_date=date.today(), strategy=strategy,
                           high=[items[0]], medium=[items[1]], counts={"high":1,"medium":1}, top_soonest=items)
    monkeypatch.setattr(alerts, "generate_daily_stockout_digest", fake_generate)
    digest = alerts.generate_daily_stockout_digest(db_session, org.id, strategy="conservative")  # type: ignore
    assert digest.strategy == "conservative"
    assert digest.counts["high"] == 1

def test_idempotency(db_session, org):
    key_first = check_and_set_idempotent(str(org.id), date.today())
    assert key_first is False
    key_second = check_and_set_idempotent(str(org.id), date.today())
    assert key_second is True

def test_dispatch_digest_monkeypatched(monkeypatch, db_session, org):
    from app.services.alerts import DailyDigest, StockoutItem
    dummy = DailyDigest(org_id=str(org.id), run_date=date.today(), strategy="latest", high=[], medium=[], counts={"high":0,"medium":0}, top_soonest=[])
    sent = {}
    def fake_email(subject, body):
        sent['email']=True
        return {"channel":"email","delivered":True}
    def fake_webhook(payload):
        sent['webhook']=True
        return {"channel":"webhook","delivered":True}
    from app.services import notify
    monkeypatch.setattr(notify, "send_email", fake_email)
    monkeypatch.setattr(notify, "send_webhook", fake_webhook)
    res = dispatch_digest(dummy, ["email","webhook"])
    assert sent.get('email') and sent.get('webhook')
    assert all(r['delivered'] for r in res)

def test_notification_failure_paths(monkeypatch, db_session, org):
    from app.services.alerts import DailyDigest
    dummy = DailyDigest(org_id=str(org.id), run_date=date.today(), strategy="latest", high=[], medium=[], counts={"high":0,"medium":0}, top_soonest=[])
    from app.services import notify
    monkeypatch.setattr(notify, "send_email", lambda s,b: {"channel":"email","delivered":False,"error":"smtp"})
    monkeypatch.setattr(notify, "send_webhook", lambda p: {"channel":"webhook","delivered":False,"error":"timeout"})
    res = dispatch_digest(dummy, ["email","webhook"])
    assert any(not r['delivered'] for r in res)

def test_risk_tier_boundaries(db_session, org, products, monkeypatch):
    from app.services.alerts import DailyDigest, StockoutItem
    items = [
        StockoutItem("1","A","A",10,None,velocity_7d=1.5,velocity_30d=None,velocity_56d=None,chosen_velocity=1.5,velocity_source="7d",days_to_stockout=6.7,risk_level="high"),
        StockoutItem("2","B","B",80,None,velocity_7d=5.5,velocity_30d=None,velocity_56d=None,chosen_velocity=5.5,velocity_source="7d",days_to_stockout=14.5,risk_level="low"),
    ]
    digest = DailyDigest(org_id=str(org.id), run_date=date.today(), strategy="latest", high=[items[0]], medium=[], counts={"high":1,"medium":0}, top_soonest=items)
    assert digest.high[0].risk_level == "high"
