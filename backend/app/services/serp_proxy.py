from __future__ import annotations

from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import (
    ProxyAuthorityEvidence, SerpManualMozValidation, SerpProxyEvaluation,
    SerpResultRow, SerpSnapshot,
)
from app.services.normalization import root_domain

CALIBRATION_UNCALIBRATED = "UNCALIBRATED_HIGH_RECALL"


def evaluate_serp_proxy(db: Session, snapshot: SerpSnapshot, required_weak: int = 4,
                        calibration_version: str = CALIBRATION_UNCALIBRATED) -> SerpProxyEvaluation:
    rows = db.scalars(select(SerpResultRow).where(SerpResultRow.snapshot_id == snapshot.id).order_by(SerpResultRow.position)).all()
    evidence_by_domain = {}
    position_evidence = {}
    for row in rows:
        domain = root_domain(row.url) or row.root_domain
        evidence = evidence_by_domain.get(domain)
        if evidence is None:
            evidence = db.scalar(select(ProxyAuthorityEvidence).where(ProxyAuthorityEvidence.root_domain == domain).order_by(ProxyAuthorityEvidence.fetched_at.desc()))
            evidence_by_domain[domain] = evidence
        dr = evidence.domain_rating if evidence else None
        if dr is None:
            category = "UNKNOWN"
        elif dr < 8:
            category = "LIKELY_WEAK"
        elif dr <= 30:
            category = "POSSIBLE_WEAK"
        else:
            category = "UNLIKELY_WEAK"
        position_evidence[str(row.position)] = {"domain": domain, "dr": dr, "category": category}
    likely = sum(x["category"] == "LIKELY_WEAK" for x in position_evidence.values())
    possible = sum(x["category"] == "POSSIBLE_WEAK" for x in position_evidence.values())
    unlikely = sum(x["category"] == "UNLIKELY_WEAK" for x in position_evidence.values())
    unknown = sum(x["category"] == "UNKNOWN" for x in position_evidence.values())
    minimum = likely
    maximum = likely + possible + unknown
    if maximum >= required_weak:
        classification, uncertainty, action = "SERP_MOZ_REVIEW", "ELEVATED", "MANUAL_MOZ_VALIDATION"
    elif unknown:
        classification, uncertainty, action = "SERP_PROXY_DATA_INCOMPLETE", "UNKNOWN", "MANUAL_MOZ_VALIDATION"
    else:
        classification, uncertainty, action = "SERP_PROXY_REJECTED_HIGH_CONFIDENCE", "EXPERIMENTAL_ONLY", "NO_MANUAL_MOZ"
    reason = f"minimum possible weak={minimum}; maximum plausible weak={maximum}; required={required_weak}"
    evaluation = db.scalar(select(SerpProxyEvaluation).where(SerpProxyEvaluation.serp_snapshot_id == snapshot.id))
    values = dict(serp_snapshot_id=snapshot.id, candidate_id=snapshot.candidate_entity_id,
                  evaluation_version="serp_proxy_v1", calibration_version=calibration_version,
                  organic_positions_available=len(rows), likely_weak_count=likely,
                  possible_weak_count=possible, unlikely_weak_count=unlikely,
                  unknown_missing_count=unknown, minimum_possible_weak=minimum,
                  maximum_plausible_weak=maximum, required_weak_count=required_weak,
                  classification=classification, reason=reason, uncertainty=uncertainty,
                  recommended_action=action, position_evidence=position_evidence,
                  evaluated_at=datetime.utcnow())
    if evaluation is None:
        evaluation = SerpProxyEvaluation(**values); db.add(evaluation)
    else:
        for key, value in values.items(): setattr(evaluation, key, value)
    db.flush()
    return evaluation


def persist_manual_moz_validation(db: Session, snapshot: SerpSnapshot,
                                  moz_da_by_position: dict[str, float | None]) -> SerpManualMozValidation:
    count = sum(value is not None and value < 10 for value in moz_da_by_position.values())
    result = "REJECTED" if count < 4 else "PASS" if count == 4 else "IDEAL"
    validation = SerpManualMozValidation(serp_snapshot_id=snapshot.id,
        candidate_id=snapshot.candidate_entity_id, positions_checked=len(moz_da_by_position),
        moz_da_by_position=moz_da_by_position, actual_da_below_10_count=count,
        result=result, provenance="manual_moz")
    db.add(validation); db.flush()
    return validation


def serp_opportunity_metrics(db: Session) -> dict:
    rows = db.scalars(select(SerpManualMozValidation)).all()
    evaluations = {e.serp_snapshot_id: e for e in db.scalars(select(SerpProxyEvaluation)).all()}
    review = [x for x in rows if evaluations.get(x.serp_snapshot_id) and evaluations[x.serp_snapshot_id].classification == "SERP_MOZ_REVIEW"]
    qualifying = [x for x in rows if x.actual_da_below_10_count >= 4]
    retained_qualifying = [x for x in qualifying if evaluations.get(x.serp_snapshot_id) and evaluations[x.serp_snapshot_id].classification == "SERP_MOZ_REVIEW"]
    rejected_qualifying = [x for x in qualifying if x not in retained_qualifying]
    return {"labelled_serps": len(rows), "review_rate": len(review) / len(evaluations) if evaluations else 0.0,
            "opportunity_recall": len(retained_qualifying) / len(qualifying) if qualifying else None,
            "serp_false_negative_rate": len(rejected_qualifying) / len(qualifying) if qualifying else None,
            "review_true_positives": len(retained_qualifying), "review_false_positives": len(review) - len(retained_qualifying),
            "proxy_reject_false_negatives": len(rejected_qualifying)}
