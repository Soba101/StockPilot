from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from datetime import date
from typing import Optional, List
from app.core.database import get_db
from app.core.config import settings
from app.models.organization import Organization
from app.services.alerts import generate_daily_stockout_digest, check_and_set_idempotent
from app.services.notify import dispatch_digest

router = APIRouter()

@router.post("/run-daily-alerts")
def run_daily_alerts(
    authorization: Optional[str] = Header(None),
    strategy: str = "latest",
    channels: str = "email,webhook",
    db: Session = Depends(get_db),
):
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ",1)[1]
    if token != settings.ALERT_CRON_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid cron token")

    orgs: List[Organization] = db.query(Organization).all()
    run_date = date.today()
    processed = []
    already = True
    alerts_sent = 0
    channel_list = [c.strip() for c in channels.split(',') if c.strip()]

    for org in orgs:
        if check_and_set_idempotent(str(org.id), run_date):
            continue
        already = False
        digest = generate_daily_stockout_digest(db, org.id, strategy=strategy)  # type: ignore
        results = dispatch_digest(digest, channel_list)
        alerts_sent += sum(1 for r in results if r.get('delivered'))
        processed.append({
            "org_id": str(org.id),
            "counts": digest.counts,
            "channels": results
        })

    return {
        "date": run_date.isoformat(),
        "orgs_processed": len(processed),
        "alerts_sent_total": alerts_sent,
        "per_org": processed,
        "already_ran": already and len(processed)==0
    }
