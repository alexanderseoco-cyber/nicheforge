"""Immutable manual Moz labels and diagnostic calibration statistics."""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import ManualMozObservation, ProxyAuthorityEvidence, ProxyCalibrationObservation
from app.services.normalization import root_domain


def import_manual_moz_labels(db: Session, labels: Iterable[tuple[str, float]], source: str = "moz_official_verified") -> list[ManualMozObservation]:
    imported = []
    for domain, da in labels:
        normalized = root_domain(domain) or domain.strip().lower()
        previous = db.scalar(select(ManualMozObservation).where(ManualMozObservation.normalized_domain == normalized).order_by(ManualMozObservation.observed_at.desc()))
        payload = {"provenance": "manual_moz", "verification_source": source}
        if previous and previous.moz_da == da:
            continue
        if previous:
            payload["supersedes_observation_id"] = previous.id
        observation = ManualMozObservation(normalized_domain=normalized, moz_da=da, source_kind="manual_moz", raw_payload=payload)
        db.add(observation); db.flush(); imported.append(observation)
        ahrefs = db.scalar(select(ProxyAuthorityEvidence).where(ProxyAuthorityEvidence.root_domain == normalized).order_by(ProxyAuthorityEvidence.fetched_at.desc()))
        if ahrefs:
            db.add(ProxyCalibrationObservation(normalized_domain=normalized, ahrefs_dr=ahrefs.domain_rating, moz_da=da, moz_da_below_10=da < 10, provenance="manual_moz", calibration_version="uncalibrated", feature_set_version="ahrefs_dr_v1", source_metadata={"manual_observation_id": observation.id, "verification_source": source}))
    db.commit()
    return imported


def calibration_statistics(db: Session, threshold: float = 10.0) -> dict:
    pairs = db.scalars(select(ProxyCalibrationObservation).where(ProxyCalibrationObservation.moz_da.is_not(None), ProxyCalibrationObservation.ahrefs_dr.is_not(None))).all()
    tp = sum(p.ahrefs_dr < threshold and p.moz_da < threshold for p in pairs)
    fp = sum(p.ahrefs_dr < threshold and p.moz_da >= threshold for p in pairs)
    fn = sum(p.ahrefs_dr >= threshold and p.moz_da < threshold for p in pairs)
    tn = sum(p.ahrefs_dr >= threshold and p.moz_da >= threshold for p in pairs)
    return {"observations": len(pairs), "da_below_10": tp + fn, "da_at_least_10": fp + tn, "dr_below_10_da_below_10": tp, "dr_below_10_da_at_least_10": fp, "dr_at_least_10_da_below_10": fn, "dr_at_least_10_da_at_least_10": tn, "recall": tp / (tp + fn) if tp + fn else None, "precision": tp / (tp + fp) if tp + fp else None, "specificity": tn / (tn + fp) if tn + fp else None, "false_negative_rate": fn / (fn + tp) if fn + tp else None, "false_positive_rate": fp / (fp + tn) if fp + tn else None, "dr_distribution_for_da_below_10": sorted(p.ahrefs_dr for p in pairs if p.moz_da < threshold), "da_distribution_for_dr_below_10": sorted(p.moz_da for p in pairs if p.ahrefs_dr < threshold), "confusion_matrix": {"true_positive": tp, "false_positive": fp, "false_negative": fn, "true_negative": tn}}
