"""Billing & Usage Metering Service Layer"""
from typing import Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func
from infrastructure.database.models import UsageRecord


def record_usage(
    db: Session,
    workspace_id: UUID,
    user_id: UUID,
    event_type: str,
    units: float,
    unit_type: str,
    cost_cents: float = 0.0,
    metadata: Optional[Dict[str, Any]] = None,
) -> UsageRecord:
    rec = UsageRecord(
        workspace_id=workspace_id,
        user_id=user_id,
        event_type=event_type,
        units=units,
        unit_type=unit_type,
        cost_cents=cost_cents,
        metadata_json=metadata,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


def get_workspace_usage_summary(db: Session, workspace_id: UUID) -> Dict[str, Any]:
    records = db.query(UsageRecord).filter(UsageRecord.workspace_id == workspace_id).all()
    total_compute_seconds = sum(r.units for r in records if r.unit_type == "seconds")
    total_tokens = sum(r.units for r in records if r.unit_type == "tokens")
    total_cost_cents = sum(r.cost_cents for r in records)

    return {
        "workspace_id": workspace_id,
        "total_records": len(records),
        "total_compute_seconds": round(total_compute_seconds, 2),
        "total_tokens": int(total_tokens),
        "total_cost_dollars": round(total_cost_cents / 100.0, 4),
    }
