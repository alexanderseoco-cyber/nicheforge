# NicheForge Mixed Handoff — Full Source Review

Generated from the current working tree on 2026-08-16.

This packet contains verbatim repository source for the principal mixed-handoff, identity, evidence-lineage, scope, preview, execution, migration, and frontend files. It is a read-only review artifact; no provider calls or application-data mutations were performed while generating it.

# FILE: backend/app/models/entities.py

```python
Exit code: 0
Wall time: 2.4 seconds
Total output lines: 765
Output:
from __future__ import annotations
from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, JSON, Boolean, UniqueConstraint, Index, Numeric, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.statuses import CandidateStatus


def uid() -> str:
    return str(uuid4())


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    profile_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    candidates: Mapped[list[Candidate]] = relationship(back_populates="project", cascade="all, delete-orphan")


class City(Base):
    __tablename__ = "cities"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(120), index=True)
    state_code: Mapped[str] = mapped_column(String(2), index=True)
    population: Mapped[int] = mapped_column(Integer, index=True)
    population_vintage: Mapped[str] = mapped_column(String(40), default="unknown")
    census_geo_id: Mapped[str | None] = mapped_column(String(30), nullable=True)
    __table_args__ = (UniqueConstraint("name", "state_code", "population_vintage", name="uq_city_vintage"),)


class CandidateEntity(Base):
    """Global logical candidate identity, independent of project membership."""
    __tablename__ = "candidate_entities"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    canonical_identity: Mapped[str] = mapped_column(String(700), unique=True, index=True)
    identity_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    service_term_normalized: Mapped[str] = mapped_column(String(240), index=True)
    city_id: Mapped[str | None] = mapped_column(ForeignKey("cities.id"), nullable=True, index=True)
    validation_scope: Mapped[str] = mapped_column(String(30), default="LOCAL_RANK_RENT", index=True)
    language_code: Mapped[str] = mapped_column(String(16), default="en")
    country_code: Mapped[str] = mapped_column(String(2), default="US")
    canonical_keyword: Mapped[str] = mapped_column(String(400))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProjectCandidate(Base):
    __tablename__ = "project_candidates"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    candidate_entity_id: Mapped[str] = mapped_column(ForeignKey("candidate_entities.id"), index=True)
    validation_scope: Mapped[str] = mapped_column(String(30), default="LOCAL_RANK_RENT", index=True)
    scope_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    search_volume_evidence_id: Mapped[str | None] = mapped_column(ForeignKey("keyword_metric_evidence.id"), nullable=True, index=True)
    original_input: Mapped[str | None] = mapped_column(String(500), nullable=True)
    broad_category: Mapped[str | None] = mapped_column(String(160), nullable=True)
    micro_niche: Mapped[str | None] = mapped_column(String(160), nullable=True)
    nano_niche: Mapped[str | None] = mapped_column(String(160), nullable=True)
    display_keyword: Mapped[str] = mapped_column(String(400))
    current_status: Mapped[str] = mapped_column(String(40), default=CandidateStatus.IMPORTED)
    automatic_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    manual_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    manual_override_reason: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    current_reason_codes: Mapped[list] = mapped_column(JSON, default=list)
    latest_run_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    __table_args__ = (UniqueConstraint("project_id", "candidate_entity_id", name="uq_project_candidate_entity"),)


class Run(Base):
    __tablename__ = "runs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    run_type: Mapped[str] = mapped_column(String(30), default="STANDARD", index=True)
    parent_run_id: Mapped[str | None] = mapped_column(ForeignKey("runs.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(30), default="CREATED", index=True)
    min_population: Mapped[int] = mapped_column(Integer)
    max_population: Mapped[int] = mapped_column(Integer)
    min_search_volume: Mapped[int] = mapped_column(Integer)
    da_threshold: Mapped[float] = mapped_column(Float)
    required_low_da_count: Mapped[int] = mapped_column(Integer)
    minimum_weak_domains: Mapped[int] = mapped_column(Integer, default=4)
    ideal_weak_domains: Mapped[int] = mapped_column(Integer, default=5)
    authority_evaluation_mode: Mapped[str] = mapped_column(String(20), default="ADAPTIVE")
    authority_batch_size: Mapped[int] = mapped_column(Integer, default=5)
    adaptive_seek_ideal: Mapped[bool] = mapped_column(Boolean, default=True)
    kd_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    kd_provider: Mapped[str] = mapped_column(String(80), default="moz")
    kd_threshold: Mapped[float] = mapped_column(Float, default=15.0)
    kd_operator: Mapped[str] = mapped_column(String(4), default="<")
    kd_mode: Mapped[str] = mapped_column(String(20), default="PRIORITY")
    organic_depth: Mapped[int] = mapped_column(Integer)
    country_code: Mapped[str] = mapped_column(String(2), default="US")
    language_code: Mapped[str] = mapped_column(String(16), default="en")
    location_config: Mapped[dict] = mapped_column(JSON, default=dict)
    enabled_gates: Mapped[dict] = mapped_column(JSON, default=dict)
    provider_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    freshness_policy_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    freshness_policy: Mapped[str] = mapped_column(String(40), default="REUSE_FRESH_ONLY")
    configuration_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    counters: Mapped[dict] = mapped_column(JSON, default=dict)
    estimated_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    proxy_provider: Mapped[str | None] = mapped_column(String(80), nullable=True)
    proxy_metric: Mapped[str | None] = mapped_column(String(80), nullable=True)
    proxy_calibration_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    proxy_configuration_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    proxy_reject_audit_percent: Mapped[float] = mapped_column(Float, default=0.0)


class RunCandidate(Base):
    __tablename__ = "run_candidates"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    project_candidate_id: Mapped[str] = mapped_column(ForeignKey("project_candidates.id"), index=True)
    validation_scope: Mapped[str] = mapped_column(String(30), default="LOCAL_RANK_RENT", index=True)
    authority_opportunity_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default=CandidateStatus.IMPORTED)
    automatic_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    reason_codes: Mapped[list] = mapped_column(JSON, default=list)
    population_evidence_id: Mapped[str | None] = mapped_column(ForeignKey("population_evidence.id"), nullable=True)
    search_volume_evidence_id: Mapped[str | None] = mapped_column(ForeignKey("search_volume_evidence.id"), nullable=True)
    keyword_difficulty_evidence_id: Mapped[str | None] = mapped_column(ForeignKey("keyword_difficulty_evidence.id"), nullable=True)
    serp_snapshot_id: Mapped[str | None] = mapped_column(ForeignKey("serp_snapshots.id"), nullable=True)
    da_threshold_used: Mapped[float | None] = mapped_column(Float, nullable=True)
    required_low_da_count_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    minimum_weak_domains_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ideal_weak_domains_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    authority_evaluation_mode_used: Mapped[str | None] = mapped_column(String(20), nullable=True)
    authority_targets_evaluated: Mapped[int | None] = mapped_column(Integer, nullable=True)
    authority_targets_cached: Mapped[int | None] = mapped_column(Integer, nullable=True)
    authority_targets_fetched: Mapped[int | None] = mapped_column(Integer, nullable=True)
    authority_targets_unchecked: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confirmed_weak_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    opportunity_classification: Mapped[str | None] = mapped_column(String(30), nullable=True)
    adaptive_seek_ideal_used: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    organic_results_evaluated: Mapped[int | None] = mapped_column(Integer, nullable=True)
    authority_results_available: Mapped[int | None] = mapped_column(Integer, nullable=True)
    low_da_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    primary_gate_passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    kd_value_used: Mapped[float | None] = mapped_column(Float, nullable=True)
    kd_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    proxy_classification: Mapped[str | None] = mapped_column(String(40), nullable=True)
    proxy_result: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    __table_args__ = (UniqueConstraint("run_id", "project_candidate_id", name="uq_run_project_candidate"),)


class CandidateEvent(Base):
    __tablename__ = "candidate_events"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    run_id: Mapped[str | None] = mapped_column(ForeignKey("runs.id"), nullable=True, index=True)
    run_candidate_id: Mapped[str | None] = mapped_column(ForeignKey("run_candidates.id"), nullable=True, index=True)
    project_candidate_id: Mapped[str] = mapped_column(ForeignKey("project_candidates.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    previous_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    resulting_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    reason_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    evidence_references: Mapped[dict] = mapped_column(JSON, default=dict)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class RunCandidateAuthorityEvidence(Base):
    __tablename__ = "run_candidate_authority_evidence"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    run_candidate_id: Mapped[str] = mapped_column(ForeignKey("run_candidates.id"), index=True)
    serp_result_row_id: Mapped[str] = mapped_column(ForeignKey("serp_results.id"), index=True)
    authority_evidence_id: Mapped[str] = mapped_column(ForeignKey("authority_evidence.id"), index=True)
    ranking_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    da_value_used: Mapped[float | None] = mapped_column(Float, nullable=True)
    counted_as_low_da: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("run_candidate_id", "serp_result_row_id", name="uq_run_candidate_serp_authority"),)


class PopulationEvidence(Base):
    __tablename__ = "population_evidence"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    candidate_entity_id: Mapped[str] = mapped_column(ForeignKey("candidate_entities.id"), index=True)
    city_id: Mapped[str] = mapped_column(ForeignKey("cities.id"), index=True)
    provider: Mapped[str] = mapped_column(String(80))
    source_kind: Mapped[str] = mapped_column(String(40), default="census_csv")
    population: Mapped[int] = mapped_column(Integer)
    population_vintage: Mapped[str] = mapped_column(String(40))
    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    source_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    fresh_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class SearchVolumeEvidence(Base):
    __tablename__ = "search_volume_evidence"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    candidate_entity_id: Mapped[str] = mapped_column(ForeignKey("candidate_entities.id"), index=True)
    keyword: Mapped[str] = mapped_column(String(400), index=True)
    location_name: Mapped[str] = mapped_column(String(240), index=True)
    language_code: Mapped[str] = mapped_column(String(16), default="en")
    country_code: Mapped[str] = mapped_column(String(2), default="US")
    provider: Mapped[str] = mapped_column(String(80), index=True)
    source_kind: Mapped[str] = mapped_column(String(40), default="mock")
    avg_monthly_searches: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cpc: Mapped[float | None] = mapped_column(Float, nullable=True)
    competition: Mapped[float | None] = mapped_column(Float, nullable=True)
    monthly_history: Mapped[list] = mapped_column(JSON, default=list)
    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    request_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    fresh_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (Index("ix_sv_evidence_request", "keyword", "location_name", "language_code", "country_code"),)


class KeywordMetricQuery(Base):
    """Provider-neutral research query; independent from validation Runs."""
    __tablename__ = "keyword_metric_queries"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    submitted_keyword: Mapped[str] = mapped_column(String(400), index=True)
    normalized_keyword: Mapped[str] = mapped_column(String(400), index=True)
    location_name: Mapped[str | None] = mapped_column(String(240), nullable=True, index=True)
    location_target: Mapped[dict] = mapped_column(JSON, default=dict)
    language_code: Mapped[str] = mapped_column(String(16), default="en")
    country_code: Mapped[str] = mapped_column(String(2), default="US")
    provider: Mapped[str] = mapped_column(String(80), index=True)
    status: Mapped[str] = mapped_column(String(30), default="PENDING")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class KeywordMetricEvidence(Base):
    """Append-only keyword metrics; refreshes create new rows."""
    __tablename__ = "keyword_metric_evidence"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    query_id: Mapped[str] = mapped_column(ForeignKey("keyword_metric_queries.id"), index=True)
    submitted_keyword: Mapped[str] = mapped_column(String(400), index=True)
    provider_keyword: Mapped[str | None] = mapped_column(String(400), nullable=True, index=True)
    normalized_keyword: Mapped[str] = mapped_column(String(400), index=True)
    location_name: Mapped[str | None] = mapped_column(String(240), nullable=True, index=True)
    location_target: Mapped[dict] = mapped_column(JSON, default=dict)
    language_code: Mapped[str] = mapped_column(String(16), default="en")
    country_code: Mapped[str] = mapped_column(String(2), default="US")
    provider: Mapped[str] = mapped_column(String(80), index=True)
    source_kind: Mapped[str] = mapped_column(String(40), default="provider")
    avg_monthly_searches: Mapped[int | None] = mapped_column(Integer, nullable=True)
    competition: Mapped[float | None] = mapped_column(Float, nullable=True)
    competition_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cpc: Mapped[float | None] = mapped_column(Float, nullable=True)
    low_bid: Mapped[float | None] = mapped_column(Float, nullable=True)
    high_bid: Mapped[float | None] = mapped_column(Float, nullable=True)
    provider_currency_code: Mapped[str | None] = mapped_column(String(3), nullable=True)
    usd_cpc: Mapped[float | None] = mapped_column(Float, nullable=True)
    usd_low_bid: Mapped[float | None] = mapped_column(Float, nullable=True)
    usd_high_bid: Mapped[float | None] = mapped_column(Float, nullable=True)
    fx_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    fx_rate_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    fx_source: Mapped[str | None] = mapped_column(String(120), nullable=True)
    monthly_history: Mapped[list] = mapped_column(JSON, default=list)
    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    fresh_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    mapping_status: Mapped[str] = mapped_column(String(30), default="MAPPED")


class KeywordMetricBatch(Base):
    __tablename__ = "keyword_metric_batches"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    provider: Mapped[str] = mapped_column(String(80), index=True)
    submitted_count: Mapped[int] = mapped_column(Integer, default=0)
    deduplicated_count: Mapped[int] = mapped_column(Integer, default=0)
    returned_count: Mapped[int] = mapped_column(Integer, default=0)
    mapped_count: Mapped[int] = mapped_column(Integer, default=0)
    unmapped_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(30), default="PENDING")
    cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ProviderGeoMapping(Base):
    """Persistent provider-specific mapping for a canonical city identity."""
    __tablename__ = "provider_geo_mappings"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    city: Mapped[str] = mapped_column(String(120), index=True)
    state_code: Mapped[str] = mapped_column(String(8), index=True)
    country_code: Mapped[str] = mapped_column(String(2), default="US", index=True)
    provider: Mapped[str] = mapped_column(String(80), index=True)
    criterion_id: Mapped[str] = mapped_column(String(80))
    resource_name: Mapped[str] = mapped_column(String(200))
    provider_name: Ma…2395 tokens truncated…ed[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project: Mapped[Project] = relationship(back_populates="candidates")
    city: Mapped[City | None] = relationship()

    __table_args__ = (UniqueConstraint("project_id", "normalized_keyword", name="uq_project_keyword"),)


class SerpSnapshot(Base):
    __tablename__ = "serp_snapshots"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates.id"), index=True)
    provider: Mapped[str] = mapped_column(String(80))
    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    candidate_entity_id: Mapped[str | None] = mapped_column(ForeignKey("candidate_entities.id"), nullable=True, index=True)
    keyword: Mapped[str | None] = mapped_column(String(400), nullable=True)
    location_name: Mapped[str | None] = mapped_column(String(240), nullable=True)
    language_code: Mapped[str] = mapped_column(String(16), default="en")
    country_code: Mapped[str] = mapped_column(String(2), default="US")
    device_profile: Mapped[str] = mapped_column(String(30), default="desktop")
    requested_depth: Mapped[int] = mapped_column(Integer, default=10)
    source_kind: Mapped[str] = mapped_column(String(40), default="mock")
    fresh_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class SerpResultRow(Base):
    __tablename__ = "serp_results"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("serp_snapshots.id"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    title: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    url: Mapped[str] = mapped_column(String(2000))
    root_domain: Mapped[str] = mapped_column(String(500), index=True)
    display_domain: Mapped[str | None] = mapped_column(String(500), nullable=True)
    result_type: Mapped[str | None] = mapped_column(String(60), nullable=True)
    raw_row: Mapped[dict] = mapped_column(JSON, default=dict)


class SerpProxyEvaluation(Base):
    __tablename__ = "serp_proxy_evaluations"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    serp_snapshot_id: Mapped[str] = mapped_column(ForeignKey("serp_snapshots.id"), unique=True, index=True)
    candidate_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    evaluation_version: Mapped[str] = mapped_column(String(80), default="serp_proxy_v1")
    calibration_version: Mapped[str] = mapped_column(String(80), default="UNCALIBRATED_HIGH_RECALL")
    organic_positions_available: Mapped[int] = mapped_column(Integer, default=0)
    likely_weak_count: Mapped[int] = mapped_column(Integer, default=0)
    possible_weak_count: Mapped[int] = mapped_column(Integer, default=0)
    unlikely_weak_count: Mapped[int] = mapped_column(Integer, default=0)
    unknown_missing_count: Mapped[int] = mapped_column(Integer, default=0)
    minimum_possible_weak: Mapped[int] = mapped_column(Integer, default=0)
    maximum_plausible_weak: Mapped[int] = mapped_column(Integer, default=0)
    required_weak_count: Mapped[int] = mapped_column(Integer, default=4)
    classification: Mapped[str] = mapped_column(String(50))
    reason: Mapped[str] = mapped_column(String(2000))
    uncertainty: Mapped[str] = mapped_column(String(100))
    recommended_action: Mapped[str] = mapped_column(String(100))
    position_evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SerpManualMozValidation(Base):
    __tablename__ = "serp_manual_moz_validations"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    serp_snapshot_id: Mapped[str] = mapped_column(ForeignKey("serp_snapshots.id"), index=True)
    candidate_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    positions_checked: Mapped[int] = mapped_column(Integer, default=0)
    moz_da_by_position: Mapped[dict] = mapped_column(JSON, default=dict)
    actual_da_below_10_count: Mapped[int] = mapped_column(Integer, default=0)
    result: Mapped[str] = mapped_column(String(30))
    validation_status: Mapped[str] = mapped_column(String(30), default="INCOMPLETE")
    unavailable_positions: Mapped[list] = mapped_column(JSON, default=list)
    mismatched_domains: Mapped[dict] = mapped_column(JSON, default=dict)
    provenance: Mapped[str] = mapped_column(String(40), default="manual_moz")
    validated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AuthorityEvidence(Base):
    __tablename__ = "authority_evidence"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    candidate_entity_id: Mapped[str | None] = mapped_column(ForeignKey("candidate_entities.id"), nullable=True, index=True)
    target_url: Mapped[str] = mapped_column(String(2000), index=True)
    root_domain: Mapped[str] = mapped_column(String(500), index=True)
    target_type: Mapped[str] = mapped_column(String(20))
    provider: Mapped[str] = mapped_column(String(80), index=True)
    source_kind: Mapped[str] = mapped_column(String(40), default="mock")
    da: Mapped[float | None] = mapped_column(Float, nullable=True)
    pa: Mapped[float | None] = mapped_column(Float, nullable=True)
    spam_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    linking_root_domains: Mapped[int | None] = mapped_column(Integer, nullable=True)
    backlinks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    request_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    fresh_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AuthorityMetric(Base):
    __tablename__ = "authority_metrics"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    target_key: Mapped[str] = mapped_column(String(2000), index=True)
    target_type: Mapped[str] = mapped_column(String(20))
    provider: Mapped[str] = mapped_column(String(80), index=True)
    da: Mapped[float | None] = mapped_column(Float, nullable=True)
    pa: Mapped[float | None] = mapped_column(Float, nullable=True)
    spam_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    linking_root_domains: Mapped[int | None] = mapped_column(Integer, nullable=True)
    backlinks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ProxyAuthorityEvidence(Base):
    __tablename__ = "proxy_authority_evidence"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    target_url: Mapped[str] = mapped_column(String(2000), index=True)
    root_domain: Mapped[str] = mapped_column(String(500), index=True)
    provider: Mapped[str] = mapped_column(String(80), index=True, default="ahrefs")
    metric: Mapped[str] = mapped_column(String(80), default="domain_rating")
    domain_rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_kind: Mapped[str] = mapped_column(String(40), default="ahrefs_api")
    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    request_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    fresh_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ProxyBacklinkFeatureEvidence(Base):
    __tablename__ = "proxy_backlink_feature_evidence"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    target_domain: Mapped[str] = mapped_column(String(500), index=True)
    provider: Mapped[str] = mapped_column(String(80), default="dataforseo", index=True)
    operation: Mapped[str] = mapped_column(String(100), default="backlinks_bulk_pages_summary_live")
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    backlinks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    referring_domains: Mapped[int | None] = mapped_column(Integer, nullable=True)
    referring_main_domains: Mapped[int | None] = mapped_column(Integer, nullable=True)
    referring_ips: Mapped[int | None] = mapped_column(Integer, nullable=True)
    referring_subnets: Mapped[int | None] = mapped_column(Integer, nullable=True)
    referring_domains_nofollow: Mapped[int | None] = mapped_column(Integer, nullable=True)
    referring_main_domains_nofollow: Mapped[int | None] = mapped_column(Integer, nullable=True)
    backlinks_spam_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    request_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    fresh_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    actual_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    api_status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    api_status_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    mapping_status: Mapped[str] = mapped_column(String(40), default="mapped")
    mapping_error: Mapped[str | None] = mapped_column(String(1000), nullable=True)


class ProxyCalibrationObservation(Base):
    __tablename__ = "proxy_calibration_observations"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    normalized_domain: Mapped[str] = mapped_column(String(500), index=True)
    ahrefs_dr: Mapped[float | None] = mapped_column(Float, nullable=True)
    moz_da: Mapped[float | None] = mapped_column(Float, nullable=True)
    provenance: Mapped[str] = mapped_column(String(40), default="manual_moz")
    calibration_version: Mapped[str] = mapped_column(String(80), default="uncalibrated")
    observed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    source_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    dataforseo_features: Mapped[dict] = mapped_column(JSON, default=dict)
    moz_da_below_10: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    feature_set_version: Mapped[str] = mapped_column(String(80), default="ahrefs_dr_v1")


class ManualMozObservation(Base):
    __tablename__ = "manual_moz_observations"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    normalized_domain: Mapped[str] = mapped_column(String(500), index=True)
    moz_da: Mapped[float | None] = mapped_column(Float, nullable=True)
    moz_pa: Mapped[float | None] = mapped_column(Float, nullable=True)
    spam_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_kind: Mapped[str] = mapped_column(String(40), default="manual_moz")
    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    observed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ProviderCache(Base):
    __tablename__ = "provider_cache"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    cache_key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    provider: Mapped[str] = mapped_column(String(80), index=True)
    operation: Mapped[str] = mapped_column(String(100))
    evidence_type: Mapped[str] = mapped_column(String(60))
    evidence_id: Mapped[str] = mapped_column(String(36))
    status: Mapped[str] = mapped_column(String(30), default="usable")
    fetched_at: Mapped[datetime] = mapped_column(DateTime)
    fresh_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProviderCall(Base):
    __tablename__ = "provider_calls"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    provider: Mapped[str] = mapped_column(String(80), index=True)
    execution_mode: Mapped[str | None] = mapped_column(String(20), nullable=True)
    stage: Mapped[str] = mapped_column(String(60), index=True)
    operation: Mapped[str] = mapped_column(String(100))
    request_cache_key: Mapped[str] = mapped_column(String(128), index=True)
    outcome: Mapped[str] = mapped_column(String(30))
    cache_hit: Mapped[bool] = mapped_column(Boolean, default=False)
    source_kind: Mapped[str] = mapped_column(String(40), default="live_api")
    units: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    estimated_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    error_category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    # Keyword-metrics chunk telemetry. These describe an actual attempt, not
    # planner output; planned counts remain on the batch/run report.
    customer_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    target_identity: Mapped[str | None] = mapped_column(String(240), nullable=True, index=True)
    geo_target_resource: Mapped[str | None] = mapped_column(String(240), nullable=True)
    language_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    chunk_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chunk_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    submitted_keyword_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    attempt_number: Mapped[int] = mapped_column(Integer, default=1)
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    provider_reached: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    operation_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    run_id: Mapped[str | None] = mapped_column(ForeignKey("runs.id"), nullable=True, index=True)
    run_candidate_id: Mapped[str | None] = mapped_column(ForeignKey("run_candidates.id"), nullable=True, index=True)


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    display_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(500))
    role: Mapped[str] = mapped_column(String(20), default="USER", index=True)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class UserSession(Base):
    __tablename__ = "user_sessions"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    refresh_token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    client_type: Mapped[str] = mapped_column(String(20), default="WEB")


class UserProviderQuota(Base):
    __tablename__ = "user_provider_quotas"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    provider: Mapped[str] = mapped_column(String(80), index=True)
    daily_allowance: Mapped[int] = mapped_column(Integer, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    __table_args__ = (UniqueConstraint("user_id", "provider", name="uq_user_provider_quota"),)


class UserQuotaBonus(Base):
    __tablename__ = "user_quota_bonuses"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    provider: Mapped[str] = mapped_column(String(80), index=True)
    operations: Mapped[int] = mapped_column(Integer)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RunReservation(Base):
    __tablename__ = "run_reservations"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    provider: Mapped[str] = mapped_column(String(80), index=True)
    batch_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    reserved_operations: Mapped[int] = mapped_column(Integer)
    consumed_operations: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class UserProviderUsage(Base):
    __tablename__ = "user_provider_usage"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    provider: Mapped[str] = mapped_column(String(80), index=True)
    reservation_id: Mapped[str | None] = mapped_column(ForeignKey("run_reservations.id"), nullable=True, index=True)
    provider_call_id: Mapped[str | None] = mapped_column(ForeignKey("provider_calls.id"), nullable=True, index=True)
    operation_count: Mapped[int] = mapped_column(Integer, default=0)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class ImportBatch(Base):
    __tablename__ = "import_batches"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    source_kind: Mapped[str] = mapped_column(String(40))
    provider: Mapped[str | None] = mapped_column(String(80), nullable=True)
    file_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    accepted_count: Mapped[int] = mapped_column(Integer, default=0)
    rejected_count: Mapped[int] = mapped_column(Integer, default=0)
    error_summary: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


```

# FILE: backend/app/services/identity.py

```python
Exit code: 0
Wall time: 1.7 seconds
Output:
from __future__ import annotations

import hashlib
import unicodedata

from app.services.normalization import normalize_keyword


def canonical_identity(service_term: str, geographic_id: str, language_code: str = "en", country_code: str = "US") -> str:
    """Build identity from canonical fields, never display text."""
    service = unicodedata.normalize("NFKC", normalize_keyword(service_term))
    geo = unicodedata.normalize("NFKC", geographic_id.strip().lower())
    language = language_code.strip().lower()
    country = country_code.strip().upper()
    if not service or not geo or not language or not country:
        raise ValueError("service, geographic identity, language, and country are required")
    return "|".join((service, geo, language, country))


def identity_key(canonical: str) -> str:
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


```

# FILE: backend/app/services/validation_scope.py

```python
Exit code: 0
Wall time: 1.5 seconds
Output:
from dataclasses import dataclass


LOCAL_SCOPE = "LOCAL_RANK_RENT"
GENERAL_SCOPE = "GENERAL_NICHE"


@dataclass(frozen=True)
class ScopeDecision:
    scope: str
    reason: str
    requires_location: bool


def resolve_scope(*, location_target: dict | None, has_local_city_match: bool) -> ScopeDecision:
    """Classify once at handoff boundary; never invent a city for general terms."""
    target = location_target or {}
    explicit_city = bool(target.get("city") or target.get("city_id") or target.get("state_code"))
    if explicit_city:
        return ScopeDecision(LOCAL_SCOPE, "EXPLICIT_CITY_TARGET", True)
    if has_local_city_match:
        return ScopeDecision(LOCAL_SCOPE, "LOCAL_KEYWORD_MATCH", True)
    return ScopeDecision(GENERAL_SCOPE, "COUNTRY_TARGET_WITHOUT_LOCAL_MATCH", False)


```

# FILE: backend/app/api/routes.py

```python
Exit code: 0
Wall time: 1.6 seconds
Total output lines: 720
Output:
import logging
import re
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import select, or_
from datetime import datetime

from app.db.session import get_db
from app.models.entities import ImportBatch, Project, City, Candidate, Run, RunCandidate, CandidateEntity, ProjectCandidate, SerpSnapshot, SerpResultRow, RunCandidateAuthorityEvidence, AuthorityEvidence, KeywordMetricEvidence
from app.schemas.domain import (ProjectCreate, ProjectHandoffAttachRequest, ProjectHandoffAttachResponse, CandidateGenerateRequest, CandidateOut, RunRequest, RunCreate, RunOut, ValidationProfile, OverlayRequest, KeywordMetricsRequest, KeywordMetricsPreview, KeywordMetricsResearchResponse, KeywordMetricResultOut, KeywordMetricsHandoffRequest, KeywordMetricsHandoffResponse, KeywordMetricsBatchRequest, KeywordMetricsHandoffOut)
from app.services.normalization import normalize_keyword, build_keyword
from app.services.identity import canonical_identity, identity_key
from app.services.validation_scope import GENERAL_SCOPE, LOCAL_SCOPE, resolve_scope
from app.services.gates import population_gate
from app.services.pipeline import process_candidate
from app.providers.factory import authority_provider
from app.providers.contracts import AuthorityTarget
from app.services.normalization import root_domain
from app.services.run_pipeline import execute_run
from app.services.proxy_authority import evaluate_run_candidate_proxy
from app.services.recalculation import preview_recalculation, recalculate, ledger, candidate_history
from app.services.imports import export_candidate_history_csv, export_project_csv, export_run_csv, import_cities, import_keyword_export, import_manual_evidence, import_manual_moz_csv, import_moz, import_niches
from app.providers.factory import keyword_metrics_provider
from app.providers.contracts import KeywordMetricRequest
from app.models.entities import KeywordMetricQuery, KeywordMetricEvidence, KeywordMetricBatch, KeywordMetricValidationHandoff, ProviderCountryGeoMapping, KeywordOpportunityMetrics, ProviderCall
from app.services.keyword_metrics_batch import KeywordMetricsBatchOrchestrator
from app.services.keyword_metrics_multi_city import MultiCityKeywordMetricsOrchestrator, StructuredLocation
from app.providers.google_ads_geo import GoogleAdsGeoTargetResolver
from app.core.config import get_settings
from app.api.auth_routes import get_current_user
from app.models.entities import User, RunReservation
from app.services.user_quotas import reserve, finish, snapshot
from app.providers.keyword_metrics_safety import KeywordMetricsGuardError
from app.services.currency_normalization import normalize_to_usd
from app.services.customer_currency import resolve_cached_customer_currency
from app.services.monetary_enrichment import resolve_usd_metrics
from app.services.derived_metrics import calculate_derived_metrics
from app.api.auth_routes import require_admin

router = APIRouter(prefix="/api/v1")
logger = logging.getLogger(__name__)

@router.get("/app/capabilities")
def app_capabilities():
    settings = get_settings()
    return {"single_user_mode": bool(settings.nicheforge_single_user_mode)}

@router.get("/geo/countries")
def country_geo_capabilities(db: Session = Depends(get_db)):
    rows = db.query(ProviderCountryGeoMapping).filter_by(provider="google_ads", mapping_status="MAPPED").all()
    return [{"country_code": row.country_code, "provider": row.provider, "criterion_id": row.criterion_id, "resource_name": row.resource_name, "target_type": row.target_type, "status": row.mapping_status, "provenance": row.provenance} for row in rows]


def _metric_requests(payload: KeywordMetricsRequest):
    return [KeywordMetricRequest(keyword=k, location_name=payload.target.location_name,
        language_code=payload.target.language_code, country_code=payload.target.country_code,
        location_target=payload.target.location_target) for k in payload.keywords]


@router.post("/keyword-metrics/preview", response_model=KeywordMetricsPreview)
async def keyword_metrics_preview(payload: KeywordMetricsRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    requests = _metric_requests(payload)
    unique = {(r.keyword.strip().casefold(), r.location_name, r.language_code) for r in requests}
    provider = keyword_metrics_provider(provider_name=payload.provider)
    settings = get_settings()
    chunk_size = max(1, getattr(settings, "keyword_metrics_max_batch_size", 10_000))
    now = datetime.utcnow()
    fresh = 0
    for request in requests:
        cached = db.query(KeywordMetricEvidence).filter(
            KeywordMetricEvidence.provider == provider.provider_name,
            KeywordMetricEvidence.submitted_keyword == request.keyword,
            KeywordMetricEvidence.location_name == request.location_name,
            KeywordMetricEvidence.language_code == request.language_code,
            KeywordMetricEvidence.country_code == request.country_code,
        ).order_by(KeywordMetricEvidence.fetched_at.desc()).first()
        if cached and cached.fresh_until and cached.fresh_until > now and not payload.force_refresh:
            fresh += 1
    missing = max(0, len(unique) - fresh)
    planned = (missing + chunk_size - 1) // chunk_size
    budget = getattr(settings, "google_ads_daily_operation_budget", None)
    used = db.query(ProviderCall).filter(
        ProviderCall.provider == provider.provider_name,
        ProviderCall.customer_id == settings.google_ads_customer_id,
        ProviderCall.started_at >= datetime(now.year, now.month, now.day),
        ProviderCall.operation_count == 1,
    ).count() if provider.provider_name == "google_ads" else 0
    remaining = max(0, budget - used) if budget is not None else None
    user_allowance = snapshot(db, user.id, payload.provider)
    return KeywordMetricsPreview(submitted_count=len(requests), deduplicated_count=len(unique), cache_hits=fresh,
        provider_requests=0, estimated_cost=0.0, transport_would_occur=False, provider=provider.provider_name,
        total_combinations=len(unique), fresh_cache_savings=fresh,
        keywords_requiring_provider_evidence=missing, target_count=1,
        language_count=len({r.language_code for r in requests}), chunk_size=chunk_size,
        planned_rpc_count=planned, operation_budget_status=("CONFIGURED" if budget is not None else "UNKNOWN_UNVERIFIED"),
        provider_capacity_remaining=remaining,
        effective_executable_allowance=min(planned, remaining, user_allowance["available"]) if remaining is not None else min(planned, user_allowance["available"]))


@router.get("/keyword-metrics/provider-telemetry")
def keyword_metrics_provider_telemetry(_: object = Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.query(ProviderCall).filter(ProviderCall.stage == "keyword_metrics").all()
    return {
        "provider": "google_ads",
        "actual_attempts": len(rows),
        "successful_attempts": sum(row.outcome == "SUCCESS" for row in rows),
        "provider_rejections": sum(row.outcome == "PROVIDER_REJECTED" for row in rows),
        "pre_provider_failures": sum(row.outcome == "NETWORK_FAILURE_BEFORE_PROVIDER" for row in rows),
        "budget_rejections": sum(row.outcome == "BUDGET_EXCEEDED" for row in rows),
        "consumed_operations": sum(row.operation_count or 0 for row in rows),
        "submitted_keywords": sum(row.submitted_keyword_count or 0 for row in rows),
    }


@router.post("/keyword-metrics/research", response_model=KeywordMetricsResearchResponse)
async def keyword_metrics_research(payload: KeywordMetricsRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    requests = _metric_requests(payload); provider = keyword_metrics_provider(provider_name=payload.provider)
    batch = KeywordMetricBatch(provider=provider.provider_name, submitted_count=len(requests), status="RUNNING")
    db.add(batch); db.flush()
    reservation = None
    try:
        settings = get_settings()
        planned = (len({r.keyword.strip().casefold() for r in requests}) + max(1, getattr(settings, "keyword_metrics_max_batch_size", 10_000)) - 1) // max(1, getattr(settings, "keyword_metrics_max_batch_size", 10_000))
        try:
            reservation = reserve(db, user.id, provider.provider_name, planned, batch.id, getattr(settings, "google_ads_daily_operation_budget", None), getattr(settings, "google_ads_customer_id", None))
        except ValueError as exc:
            db.rollback(); raise HTTPException(status_code=409, detail=str(exc)) from exc
        result = await KeywordMetricsBatchOrchestrator(
            provider, db=db, customer_id=settings.google_ads_customer_id
        ).execute(requests)
    except KeywordMetricsGuardError as exc:
        if reservation: finish(db, reservation, 0)
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        if reservation: finish(db, reservation, 0)
        logger.exception("Keyword metrics research failed before response serialization")
        # Keep provider/runtime failures JSON-shaped so browser clients receive
        # a readable API error instead of a CORS-looking network failure.
        safe_type = type(exc).__name__
        raise HTTPException(status_code=502, detail=f"Google Ads search-volume request failed ({safe_type}).") from exc
    for request in requests:
        query = KeywordMetricQuery(submitted_keyword=request.keyword, normalized_keyword=request.keyword.strip().casefold(), location_name=request.location_name, location_target=request.location_target or {}, language_code=request.language_code, country_code=request.country_code, provider=provider.provider_name, status=result.mapping_status.get(request.keyword, "UNMAPPED"))
        db.add(query); db.flush(); item=result.results.get(request.keyword)
        evidence = None
        if item and result.mapping_status.get(request.keyword) != "UNMAPPED":
            # Never infer currency from the target country or a USD default.
            # Unknown currency keeps provider amounts, while USD fields remain null.
            settings = get_settings()
            currency_resolution = resolve_cached_customer_currency(db, provider=item.provider, customer_id=settings.google_ads_customer_id, override=item.provider_currency_code)
            currency = currency_resolution.currency_code
            item.provider_currency_code = currency
            usd = resolve_usd_metrics(db, provider_currency=currency, cpc=item.cpc, low_bid=item.low_bid, high_bid=item.high_bid, customer_id=settings.google_ads_customer_id)
            item.usd_cpc, item.usd_low_bid, item.usd_high_bid = usd.usd_cpc, usd.usd_low_bid, usd.usd_high_bid
            item.fx_rate, item.fx_rate_date, item.fx_source = usd.fx_rate, usd.fx_rate_date, usd.fx_source
            db.add(KeywordMetricEvidence(query_id=query.id, submitted_keyword=request.keyword, provider_keyword=item.provider_keyword or item.keyword, normalized_keyword=request.keyword.strip().casefold(), location_name=request.location_name, location_target=request.location_target or {}, language_code=request.language_code, country_code=request.country_code, provider=item.provider, source_kind=item.provider, avg_monthly_searches=item.avg_monthly_searches, competition=item.competition, competition_index=item.competition_index, cpc=item.cpc, low_bid=item.low_bid, high_bid=item.high_bid, provider_currency_code=item.provider_currency_code, usd_cpc=item.usd_cpc, usd_low_bid=item.usd_low_bid, usd_high_bid=item.usd_high_bid, fx_rate=item.fx_rate, fx_rate_date=item.fx_rate_date, fx_source=item.fx_source, monthly_history=item.monthly_history, raw_payload=item.raw or {}, cost=item.cost, mapping_status=result.mapping_status.get(request.keyword, "MAPPED")))
    if reservation:
        consumed = int(sum((row.operation_count or 0) for row in db.query(ProviderCall).filter(ProviderCall.stage == "keyword_metrics", ProviderCall.started_at >= batch.created_at).all()))
        finish(db, reservation, consumed)
    batch.returned_count=len(result.results) - result.unmapped_count; batch.mapped_count=batch.returned_count; batch.unmapped_count=result.unmapped_count; batch.status="COMPLETED"; batch.cost=0.0; db.commit()
    output=[]
    for k, v in result.results.items():
        derived = None
        if result.mapping_status.get(k) != "UNMAPPED":
            derived = calculate_derived_metrics(v.avg_monthly_searches, v.usd_cpc)
            evidence = db.query(KeywordMetricEvidence).filter_by(submitted_keyword=k, provider=v.provider).order_by(KeywordMetricEvidence.fetched_at.desc()).first()
            if evidence:
                stored = db.query(KeywordOpportunityMetrics).filter_by(keyword_metric_evidence_id=evidence.id, calculation_version=derived.calculation_version, ctr_model_version=derived.ctr_model_version).first()
                if stored is None:
                    stored = KeywordOpportunityMetrics(keyword_metric_evidence_id=evidence.id, commercial_search_value=derived.commercial_search_value, projected_metrics=derived.projected, ctr_model_version=derived.ctr_model_version, calculation_version=derived.calculation_version)
                    db.add(stored); db.flush()
                derived = type("StoredDerived", (), {"commercial_search_value": stored.commercial_search_value, "ctr_model_version": stored.ctr_model_version, "projected": stored.projected_metrics})()
        evidence_id = evidence.id if result.mapping_status.get(k) != "UNMAPPED" and evidence else None
        output.append(KeywordMetricResultOut(id=evidence_id, submitted_keyword=k, provider=v.provider, provider_keyword=v.provider_keyword or v.keyword, location_name=payload.target.location_name, location_target=payload.target.location_target, language_code=payload.target.language_code, country_code=payload.target.country_code, avg_monthly_searches=v.avg_monthly_searches, cpc=v.cpc, competition=v.competition, competition_index=v.competition_index, low_bid=v.low_bid, high_bid=v.high_bid, provider_currency_code=v.provider_currency_code, usd_cpc=v.usd_cpc, usd_low_bid=v.usd_low_bid, usd_high_bid=v.usd_high_bid, fx_rate=v.fx_rate, fx_rate_date=v.fx_rate_date, fx_source=v.fx_source, monthly_history=v.monthly_history, mapping_status=result.mapping_status.get(k,"MAPPED"), cost=v.cost, commercial_metrics=None if derived is None else {"commercial_search_value": derived.commercial_search_value, "ctr_model_version": derived.ctr_model_version, "projected": derived.projected}))
    db.commit()
    return KeywordMetricsResearchResponse(batch_id=batch.id, status=batch.status, provider=provider.provider_name, submitted_count=len(requests), mapped_count=len(result.results) - result.unmapped_count, unmapped_count=result.unmapped_count, provider_requests=result.provider_requests, results=output)


@router.get("/keyword-metrics")
def keyword_metrics_list(db: Session = Depends(get_db)):
    return [{"id": x.id, "keyword": x.submitted_keyword, "provider": x.provider, "status": x.mapping_status, "search_volume": x.avg_monthly_searches, "cost": x.cost, "fetched_at": x.fetched_at} for x in db.query(KeywordMetricEvidence).order_by(KeywordMetricEvidence.fetched_at.desc()).all()]


@router.get("/keyword-metrics/{evidence_id}")
def keyword_metrics_detail(evidence_id: str, db: Session = Depends(get_db)):
    item = db.get(KeywordMetricEvidence, evidence_id)
    if not item: raise HTTPException(404, "Keyword metric evidence not found")
    return item


@router.post("/keyword-metrics/refresh", response_model=KeywordMetricsResearchResponse)
async def keyword_metrics_refresh(payload: KeywordMetricsRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return await keyword_metrics_research(payload, user, db)


@router.post("/keyword-metrics/research-batch")
async def keyword_metrics_research_batch(payload: KeywordMetricsBatchRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Resumable structured-location research; policy is calculated without transport."""
    if payload.provider != "google_ads":
        raise HTTPException(400, "research-batch requires explicit provider=google_ads")
    provider = keyword_metrics_provider(provider_name=payload.provider)
    batch = KeywordMetricBatch(provider=provider.provider_name, submitted_count=len(payload.keywords) * len(payload.locations), status="RUNNING")
    db.add(batch); db.flush()
    settings = get_settings()
    planned = (len(payload.keywords) + max(1, settings.keyword_metrics_max_batch_size) - 1) // max(1, settings.keyword_metrics_max_batch_size) * len(payload.locations)
    try:
        reservation = reserve(db, user.id, provider.provider_name, planned, batch.id, getattr(settings, "google_ads_daily_operation_budget", None), getattr(settings, "google_ads_customer_id", None))
    except ValueError as exc:
        db.rollback(); raise HTTPException(status_code=409, detail=str(exc)) from exc
    resolver = GoogleAdsGeoTargetResolver(
        client_factory=getattr(provider, "_client", None),
        enabled=settings.google_ads_enabled, live_approved=settings.google_ads_live_approved,
        credentials_configured=all((settings.google_ads_developer_token, settings.google_ads_client_id, settings.google_ads_client_secret, settings.google_ads_refresh_token, settings.google_ads_customer_id, settings.google_ads_login_customer_id)),
        freshness_days=settings.keyword_metrics_freshness_days)
    locations = [StructuredLocation(x.city, x.state_code, x.country_code) for x in payload.locations]
    from app.providers.google_ads_keyword_metrics import language_resource
    # FX transport is opt-in.  A missing PKR->USD rate must not silently
    # trigger an external FX request during keyword research.
    try:
        report = await MultiCityKeywordMetricsOrchestrator(db, provider, resolver, fx_provider=None, customer_id=settings.google_ads_customer_id, provider_currency_code=settings.google_ads_currency_code, minimum_sv=payload.minimum_sv or 260, freshness_days=settings.keyword_metrics_freshness_days).run(payload.keywords, locations, batch=batch)
    except Exception:
        finish(db, reservation, 0); db.commit(); raise
    finish(db, reservation, int(report.get("provider_requests", 0)))
    for row in report["results"]:
        evidence = db.get(KeywordMetricEvidence, row.get("evidence_id")) if row.get("evidence_id") else None
        if evidence:
            sv = evidence.avg_monthly_searches
            row["rank_rent_status"] = "MISSING_EVIDENCE" if sv is None else ("ELIGIBLE_FOR_RANK_RENT_PIPELINE" if payload.minimum_sv is None or sv >= payload.minimum_sv else "BELOW_SV_THRESHOLD")
    return {"batch_id": batch.id, "status": batch.status, "provider": provider.provider_name, "submitted_count": batch.submitted_count, **report}


@router.post("/keyword-metrics/send-to-validation", response_model=KeywordMetricsHandoffResponse)
def keyword_metrics_handoff(payload: KeywordMetricsHandoffRequest, db: Session = Depends(get_db)):
    handoffs=[]; existing_ids=[]; new_ids=[]; existing_handoff_ids=[]; new_handoff_ids=[]
    for evidence_id in dict.fromkeys(payload.evidence_ids):
        evidence=db.get(KeywordMetricEvidence, evidence_id)
        if not evidence: raise HTTPException(404, f"Keyword metric evidence not found: {evidence_id}")
        existing = db.query(KeywordMetricValidationHandoff).filter_by(evidence_id=evidence.id).order_by(KeywordMetricValidationHandoff.created_at.asc()).first()
        if existing:
            existing_ids.append(evidence.id)
            existing_handoff_ids.append(existing.id)
            handoffs.append(existing)
            continue
        handoff=KeywordMetricValidationHandoff(evidence_id=evidence.id, submitted_keyword=evidence.submitted_keyword, provider=evidence.provider, provider_keyword=evidence.provider_keyword, location_target=evidence.location_…4048 tokens truncated…jects/{project_id}/handoffs/attach", response_model=ProjectHandoffAttachResponse)
def attach_project_handoffs(project_id: str, payload: ProjectHandoffAttachRequest, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project: raise HTTPException(404, "Project not found")
    pending = []
    ready_ids = []
    for handoff_id in dict.fromkeys(payload.handoff_ids):
        handoff = db.get(KeywordMetricValidationHandoff, handoff_id)
        if not handoff: raise HTTPException(404, "Search Volume handoff not found")
        target = {**(handoff.location_target or {}), **payload.location_overrides.get(handoff_id, {})}
        embedded = _local_city_matches(db, handoff.submitted_keyword)
        scope = resolve_scope(location_target=target, has_local_city_match=bool(embedded))
        if scope.scope == LOCAL_SCOPE and not (target.get("city") or target.get("city_name") or target.get("state_code") or target.get("state")) and len(embedded) != 1:
            if embedded:
                pending.append({"handoff_id": handoff.id, "status": "LOCAL_LOCATION_REQUIRED", "validation_scope": LOCAL_SCOPE, "keyword": handoff.submitted_keyword, "city_candidates": [{"city": c.name, "state": c.state_code, "city_id": c.id} for c in embedded]})
                continue
        ready_ids.append(handoff_id)
    created, existing, ids = _attach_handoffs(db, project, ready_ids, payload.location_overrides) if ready_ids else (0, 0, [])
    db.commit()
    ready_results = [{"handoff_id": h.id, "status": "GENERAL_READY" if db.get(ProjectCandidate, cid).validation_scope == GENERAL_SCOPE else "LOCAL_READY", "validation_scope": db.get(ProjectCandidate, cid).validation_scope, "project_candidate_id": cid, "keyword": db.get(ProjectCandidate, cid).display_keyword} for h, cid in zip([db.get(KeywordMetricValidationHandoff, hid) for hid in ready_ids], ids)]
    results = pending + ready_results
    return ProjectHandoffAttachResponse(project_id=project_id, created_count=created, existing_count=existing, project_candidate_ids=ids, results=results, summary={"total": len(results), "ready": len(ready_results), "needs_location": len(pending), "failed": 0})


@router.post("/projects")
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    p = Project(name=payload.name, description=payload.description, profile_snapshot=payload.profile.model_dump())
    db.add(p); db.flush()
    candidate_ids = []
    for handoff_id in payload.handoff_ids:
        handoff = db.get(KeywordMetricValidationHandoff, handoff_id)
        if not handoff:
            raise HTTPException(404, "Search Volume handoff not found")
        evidence = db.get(KeywordMetricEvidence, handoff.evidence_id)
        target = handoff.location_target or {}
        city_name = target.get("city") or target.get("city_name")
        state_code = target.get("state_code") or target.get("state")
        if not city_name or not state_code:
            raise HTTPException(422, "Rank & Rent candidates require a city-targeted Search Volume handoff")
        city = db.scalar(select(City).where(City.name.ilike(city_name), City.state_code == state_code.upper()))
        if not city:
            raise HTTPException(422, "The handoff city is not available in the local population registry")
        geographic_id = str((target.get("geo_target_ids") or [f"{city.name},{city.state_code}"])[0])
        canonical = canonical_identity(handoff.submitted_keyword, geographic_id, handoff.language_code, handoff.country_code)
        entity = db.scalar(select(CandidateEntity).where(CandidateEntity.identity_key == identity_key(canonical)))
        if not entity:
            entity = CandidateEntity(canonical_identity=canonical, identity_key=identity_key(canonical), service_term_normalized=normalize_keyword(handoff.submitted_keyword), city_id=city.id, language_code=handoff.language_code, country_code=handoff.country_code, canonical_keyword=handoff.submitted_keyword)
            db.add(entity); db.flush()
        candidate = db.scalar(select(ProjectCandidate).where(ProjectCandidate.project_id == p.id, ProjectCandidate.candidate_entity_id == entity.id))
        if candidate and candidate.search_volume_evidence_id and candidate.search_volume_evidence_id != handoff.evidence_id:
            raise HTTPException(409, "Project candidate already references different Search Volume evidence")
        if not candidate:
            candidate = ProjectCandidate(project_id=p.id, candidate_entity_id=entity.id, search_volume_evidence_id=handoff.evidence_id, original_input=handoff.submitted_keyword, display_keyword=handoff.submitted_keyword, current_status="IMPORTED", current_reason_codes=["SEARCH_VOLUME_HANDOFF"], broad_category="Search Volume handoff")
            db.add(candidate); db.flush()
        elif candidate.search_volume_evidence_id is None:
            candidate.search_volume_evidence_id = handoff.evidence_id
        candidate_ids.append(candidate.id)
    db.commit(); db.refresh(p)
    return {"id": p.id, "name": p.name, "profile": p.profile_snapshot, "candidate_ids": candidate_ids, "candidate_count": len(candidate_ids)}


@router.post("/cities")
def add_city(name: str, state_code: str, population: int, vintage: str = "manual", db: Session = Depends(get_db)):
    c = City(name=name.strip(), state_code=state_code.upper(), population=population, population_vintage=vintage)
    db.add(c); db.commit(); db.refresh(c)
    return {"id": c.id, "name": c.name, "state": c.state_code, "population": c.population}


@router.get("/cities")
def list_cities(min_population: int = 20000, max_population: int = 120000, db: Session = Depends(get_db)):
    rows = db.scalars(select(City).where(City.population >= min_population, City.population <= max_population).order_by(City.state_code, City.name)).all()
    return [{"id": c.id, "name": c.name, "state": c.state_code, "population": c.population} for c in rows]


@router.post("/projects/{project_id}/candidates/generate")
def generate_candidates(project_id: str, payload: CandidateGenerateRequest, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    profile = payload.profile or ValidationProfile(**project.profile_snapshot)
    stmt = select(City).where(City.population >= profile.min_population, City.population <= profile.max_population)
    if payload.state_codes:
        stmt = stmt.where(City.state_code.in_([x.upper() for x in payload.state_codes]))
    cities = db.scalars(stmt).all()
    created = 0
    for niche in payload.niches:
        for city in cities:
            if not population_gate(city.population, profile).passed:
                continue
            kw = build_keyword(niche.service_term, city.name, city.state_code)
            existing = db.scalar(select(Candidate).where(Candidate.project_id == project_id, Candidate.normalized_keyword == kw))
            if existing:
                continue
            db.add(Candidate(
                project_id=project_id, city_id=city.id, broad_category=niche.broad_category,
                micro_niche=niche.micro_niche, service_term=normalize_keyword(niche.service_term),
                normalized_keyword=kw, display_keyword=kw,
            ))
            created += 1
    db.commit()
    return {"created": created, "eligible_cities": len(cities)}


@router.get("/projects/{project_id}/candidates", response_model=list[CandidateOut])
def candidates(project_id: str, db: Session = Depends(get_db)):
    rows = db.scalars(select(Candidate).where(Candidate.project_id == project_id).order_by(Candidate.display_keyword)).all()
    return [CandidateOut(
        id=c.id, keyword=c.display_keyword, city=c.city.name if c.city else None,
        state=c.city.state_code if c.city else None, population=c.city.population if c.city else None,
        search_volume=c.search_volume, cpc=c.cpc, low_da_count=c.low_da_count,
        status=c.status, automatic_pass=c.automatic_pass, reason_codes=c.reason_codes or []
    ) for c in rows]


@router.post("/projects/{project_id}/run")
async def run_project(project_id: str, payload: RunRequest, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    profile = payload.profile or ValidationProfile(**project.profile_snapshot)
    stmt = select(Candidate).where(Candidate.project_id == project_id)
    if payload.candidate_ids:
        stmt = stmt.where(Candidate.id.in_(payload.candidate_ids))
    rows = db.scalars(stmt).all()
    processed = []
    # Synchronous MVP only. Replace with queued work in Phase 1B.
    for c in rows:
        processed.append(await process_candidate(db, c, profile))
    return {
        "processed": len(processed),
        "passes_primary": sum(1 for x in processed if x.automatic_pass is True),
        "rejected": sum(1 for x in processed if x.automatic_pass is False),
    }


@router.post("/projects/{project_id}/runs", response_model=RunOut)
def create_run(project_id: str, payload: RunCreate, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    profile = payload.profile or ValidationProfile(**project.profile_snapshot)
    run = Run(project_id=project_id, min_population=profile.min_population, max_population=profile.max_population,
              min_search_volume=profile.min_search_volume, da_threshold=profile.da_threshold,
              required_low_da_count=profile.minimum_weak_domains, minimum_weak_domains=profile.minimum_weak_domains,
              ideal_weak_domains=profile.ideal_weak_domains, authority_evaluation_mode=profile.authority_evaluation_mode,
              authority_batch_size=profile.authority_batch_size, adaptive_seek_ideal=profile.adaptive_seek_ideal, organic_depth=profile.organic_depth,
              kd_enabled=profile.kd_enabled, kd_provider=profile.kd_provider, kd_threshold=profile.kd_threshold, kd_operator=profile.kd_operator, kd_mode=profile.kd_mode,
              country_code="US", language_code="en", configuration_snapshot=profile.model_dump(),
              provider_snapshot={}, freshness_policy_snapshot={}, enabled_gates={"population": True, "search_volume": True, "authority": True})
    db.add(run); db.commit(); db.refresh(run)
    return run


def _run_response(db: Session, run: Run):
    rows = db.scalars(select(RunCandidate).where(RunCandidate.run_id == run.id)).all()
    terminal = {"PASS", "PRIMARY_REJECTED", "SV_REJECTED", "POPULATION_REJECTED", "ERROR_RETRYABLE", "ERROR_TERMINAL"}
    processed = sum(1 for row in rows if row.finished_at or row.status in terminal)
    progress = 100 if run.status == "COMPLETED" else (round(processed / len(rows) * 100) if rows else 0)
    results = []
    for row in rows:
        pc = db.get(ProjectCandidate, row.project_candidate_id)
        sv = db.get(KeywordMetricEvidence, pc.search_volume_evidence_id) if pc and pc.search_volume_evidence_id else None
        snap = db.get(SerpSnapshot, row.serp_snapshot_id) if row.serp_snapshot_id else None
        serp_rows = db.scalars(select(SerpResultRow).where(SerpResultRow.snapshot_id == snap.id).order_by(SerpResultRow.position)).all() if snap else []
        authority = []
        for link in db.scalars(select(RunCandidateAuthorityEvidence).where(RunCandidateAuthorityEvidence.run_candidate_id == row.id).order_by(RunCandidateAuthorityEvidence.ranking_position)).all():
            ev = db.get(AuthorityEvidence, link.authority_evidence_id)
            result = db.get(SerpResultRow, link.serp_result_row_id)
            authority.append({"position": link.ranking_position, "domain": result.root_domain if result else None, "url": result.url if result else None, "da": link.da_value_used, "pa": ev.pa if ev else None, "provider": ev.provider if ev else None})
        serp_reason = "SERP_PROVIDER_REQUEST_ERROR" if "SERP_PROVIDER_REQUEST_ERROR" in (row.reason_codes or []) else ("SERP_INSUFFICIENT_ORGANIC_RESULTS" if "SERP_INSUFFICIENT_ORGANIC_RESULTS" in (row.reason_codes or []) else None)
        serp_status = "RETRYABLE" if serp_reason else ("PASS" if row.serp_snapshot_id and row.status not in {"ERROR_RETRYABLE"} else "NOT RUN")
        results.append({"run_candidate_id": row.id, "project_candidate_id": row.project_candidate_id, "keyword": pc.display_keyword if pc else None, "validation_scope": row.validation_scope or (pc.validation_scope if pc else "LOCAL_RANK_RENT"), "population_applicability": "NOT_APPLICABLE" if row.validation_scope == "GENERAL_NICHE" else ("PASS" if row.population_evidence_id and row.status != "POPULATION_REJECTED" else ("REJECTED" if row.status == "POPULATION_REJECTED" else "NOT RUN")), "serp_mode": "NATIONAL" if row.validation_scope == "GENERAL_NICHE" else "LOCAL_CITY", "status": row.status, "reason_codes": row.reason_codes or [], "population": "NOT APPLICABLE" if row.validation_scope == "GENERAL_NICHE" else ("PASS" if row.population_evidence_id and row.status != "POPULATION_REJECTED" else ("REJECTED" if row.status == "POPULATION_REJECTED" else "NOT RUN")), "search_volume": "PASS" if row.search_volume_evidence_id and row.status not in {"SV_REJECTED", "POPULATION_REJECTED"} else ("REJECTED" if row.status == "SV_REJECTED" else "NOT RUN"), "search_volume_value": sv.avg_monthly_searches if sv else None, "search_volume_provider": sv.provider if sv else None, "serp": serp_status, "serp_reason": serp_reason, "serp_count": len(serp_rows), "serp_required": run.organic_depth, "serp_evidence": [{"position": item.position, "domain": item.root_domain, "url": item.url, "title": item.title} for item in serp_rows], "authority_opportunity": row.opportunity_classification if row.validation_scope == "GENERAL_NICHE" else None, "authority_opportunity_reason": row.authority_opportunity_reason, "weak_site_count": row.low_da_count, "authority_threshold": row.da_threshold_used, "da": "NOT RUN" if row.authority_results_available is None else ("PASS" if row.primary_gate_passed else "REJECTED"), "da_evidence": authority, "deep_analysis": "NOT RUN" if row.authority_results_available is None else ("NOT RUN" if row.validation_scope == "GENERAL_NICHE" and row.opportunity_classification is None else ("PASS" if row.opportunity_classification in {"PASS", "IDEAL", "STRONG_POTENTIAL", "GOOD_POTENTIAL", "POTENTIAL_NICHE"} else "FAIL")), "kd": "NOT RUN" if row.kd_status in (None, "MISSING") else row.kd_status, "final_result": "NOT PRODUCED" if row.status == "ERROR_RETRYABLE" else row.status})
    return {**{column.name: getattr(run, column.name) for column in Run.__table__.columns}, "progress": progress, "candidate_results": results}


@router.get("/runs/{run_id}", response_model=RunOut)
def get_run(run_id: str, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    return _run_response(db, run)


@router.post("/runs/{run_id}/execute", response_model=RunOut)
async def execute_run_endpoint(run_id: str, payload: RunCreate | None = None, db: Session = Depends(get_db)):
    ids = payload.candidate_ids if payload else None
    try:
        return _run_response(db, await execute_run(db, run_id, ids))
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/projects/{project_id}/recalculate/preview")
def recalculate_preview(project_id: str, payload: RunCreate, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    profile = payload.profile or ValidationProfile(**project.profile_snapshot)
    return preview_recalculation(db, project_id, profile, payload.candidate_ids)

@router.post("/projects/{project_id}/validation-preview")
def validation_preview(project_id: str, payload: RunCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Zero-network UI-4 preflight; downstream work stays conditional on fail-fast gates."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    profile = payload.profile or ValidationProfile(**project.profile_snapshot)
    preview = preview_recalculation(db, project_id, profile, payload.candidate_ids)
    return {
        "project_id": project_id,
        "project_name": project.name,
        "candidate_ids": payload.candidate_ids,
        "profile": profile.model_dump(),
        "population_policy": {"enabled": profile.population_enabled, "minimum": profile.min_population, "maximum": profile.max_population},
        "search_volume_policy": {"enabled": profile.search_volume_enabled, "minimum": profile.min_search_volume},
        "authority_policy": {"threshold": profile.da_threshold, "required_weak": profile.required_low_da_count, "ideal_weak": profile.ideal_weak_domains, "depth": profile.organic_depth},
        "kd_policy": {"enabled": profile.kd_enabled, "provider": profile.kd_provider, "threshold": profile.kd_threshold, "mode": profile.kd_mode},
        "candidate_count": preview["total_affected"],
        "evidence": preview["reusable_evidence_by_stage"],
        "fresh_work": preview["estimated_provider_calls_by_stage"],
        "conditional_work": {"serp": "CONDITIONAL_ON_POPULATION_AND_SV", "authority": "CONDITIONAL_ON_SERP", "kd": "CONDITIONAL_ON_DA_QUALIFICATION"},
        "estimated_provider_calls": preview["estimated_provider_calls"],
        "estimated_cost": preview["estimated_cost"],
        "transport_would_occur": False,
        "preview_network_requests": 0,
    }


@router.post("/projects/{project_id}/recalculate", response_model=RunOut)
async def recalculate_project(project_id: str, payload: RunCreate, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    profile = payload.profile or ValidationProfile(**project.profile_snapshot)
    return await recalculate(db, project_id, profile, candidate_ids=payload.candidate_ids)


@router.get("/projects/{project_id}/ledger")
def project_ledger(project_id: str, page: int = 1, page_size: int = 50, status: str | None = None,
                  broad_category: str | None = None, micro_niche: str | None = None,
                  nano_niche: str | None = None, state: str | None = None,
                  min_population: int | None = None, max_population: int | None = None,
                  min_sv: int | None = None, max_sv: int | None = None,
                  min_kd: float | None = None, max_kd: float | None = None,
                  kd_provider: str | None = None, kd_status: str | None = None,
                  min_low_da: int | None = None, primary_result: str | None = None,
                  reason_code: str | None = None, db: Session = Depends(get_db)):
    return ledger(db, project_id, page, min(page_size, 200), status, broad_category, micro_niche, nano_niche, state,
                  min_population, max_population, min_sv, max_sv, min_kd, max_kd, kd_provider, kd_status,
                  min_low_da, primary_result, reason_code)


@router.get("/project-candidates/{project_candidate_id}/history")
def project_candidate_history(project_candidate_id: str, db: Session = Depends(get_db)):
    return candidate_history(db, project_candidate_id)


@router.post("/overlay/metrics")
async def overlay_metrics(payload: OverlayRequest):
    targets = [AuthorityTarget(url=u, root_domain=root_domain(u)) for u in payload.urls]
    provider = authority_provider()
    metrics = await provider.fetch(targets)
    return {
        "by_url": {
            m.url: {
                "root_domain": m.root_domain, "da": m.da, "pa": m.pa,
                "spam_score": m.spam_score, "linking_root_domains": m.linking_root_domains,
                "backlinks": m.backlinks, "provider": m.provider,
            } for m in metrics
        }
    }


```

# FILE: backend/app/schemas/domain.py

```python
Exit code: 0
Wall time: 1.7 seconds
Output:
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class ValidationProfile(BaseModel):
    population_enabled: bool = True
    search_volume_enabled: bool = True
    min_population: int = 20_000
    max_population: int = 120_000
    min_search_volume: int | None = 300
    da_threshold: float = 10.0
    required_low_da_count: int = 4
    minimum_weak_domains: int = 4
    ideal_weak_domains: int = 5
    authority_evaluation_mode: str = "ADAPTIVE"
    authority_batch_size: int = 5
    adaptive_seek_ideal: bool = True
    organic_depth: int = 10
    kd_enabled: bool = True
    kd_provider: str = "moz"
    kd_threshold: float = 15.0
    kd_operator: str = "<"
    kd_mode: str = "PRIORITY"


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    profile: ValidationProfile = Field(default_factory=ValidationProfile)
    handoff_ids: list[str] = Field(default_factory=list)

class ProjectHandoffAttachRequest(BaseModel):
    handoff_ids: list[str] = Field(min_length=1)
    location_overrides: dict[str, dict] = Field(default_factory=dict)

class ProjectHandoffAttachResponse(BaseModel):
    project_id: str
    created_count: int
    existing_count: int
    project_candidate_ids: list[str]
    results: list[dict] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict)


class NicheInput(BaseModel):
    service_term: str
    broad_category: str | None = None
    micro_niche: str | None = None


class CandidateGenerateRequest(BaseModel):
    niches: list[NicheInput]
    profile: ValidationProfile | None = None
    state_codes: list[str] | None = None


class CandidateOut(BaseModel):
    id: str
    keyword: str
    city: str | None
    state: str | None
    population: int | None
    search_volume: int | None
    cpc: float | None
    low_da_count: int | None
    status: str
    automatic_pass: bool | None
    reason_codes: list


class RunRequest(BaseModel):
    candidate_ids: list[str] | None = None
    profile: ValidationProfile | None = None


class RunCreate(BaseModel):
    profile: ValidationProfile | None = None
    candidate_ids: list[str] | None = None


class RunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    status: str
    counters: dict
    min_search_volume: int
    da_threshold: float
    required_low_da_count: int
    minimum_weak_domains: int
    ideal_weak_domains: int
    authority_evaluation_mode: str
    progress: int = 0
    candidate_results: list[dict] = Field(default_factory=list)

class OverlayRequest(BaseModel):
    urls: list[str] = Field(min_length=1, max_length=20)


class KeywordMetricTarget(BaseModel):
    location_name: str | None = None
    location_target: dict = Field(default_factory=dict)
    language_code: str = "en"
    country_code: str = "US"


class KeywordMetricsRequest(BaseModel):
    keywords: list[str] = Field(min_length=1)
    target: KeywordMetricTarget = Field(default_factory=KeywordMetricTarget)
    force_refresh: bool = False
    provider: str = "google_ads"


class KeywordMetricsBatchLocation(BaseModel):
    city: str
    state_code: str
    country_code: str = "US"


class KeywordMetricsBatchRequest(BaseModel):
    keywords: list[str] = Field(min_length=1)
    locations: list[KeywordMetricsBatchLocation] = Field(min_length=1)
    language_code: str = "en"
    country_code: str = "US"
    minimum_sv: int | None = 260
    force_refresh: bool = False
    provider: str = "google_ads"


class KeywordMetricsPreview(BaseModel):
    submitted_count: int
    deduplicated_count: int
    cache_hits: int
    provider_requests: int
    estimated_cost: float | None
    transport_would_occur: bool
    provider: str
    total_combinations: int = 0
    fresh_cache_savings: int = 0
    keywords_requiring_provider_evidence: int = 0
    target_count: int = 1
    language_count: int = 1
    chunk_size: int = 10_000
    planned_rpc_count: int = 0
    operation_budget_status: str = "UNKNOWN_UNVERIFIED"
    provider_capacity_remaining: int | None = None
    effective_executable_allowance: int | None = None


class KeywordMetricResultOut(BaseModel):
    id: str | None = None
    submitted_keyword: str
    provider_keyword: str | None = None
    provider: str
    location_name: str | None = None
    location_target: dict = Field(default_factory=dict)
    language_code: str
    country_code: str
    avg_monthly_searches: int | None = None
    cpc: float | None = None
    competition: float | None = None
    competition_index: int | None = None
    low_bid: float | None = None
    high_bid: float | None = None
    provider_currency_code: str | None = None
    usd_cpc: float | None = None
    usd_low_bid: float | None = None
    usd_high_bid: float | None = None
    fx_rate: float | None = None
    fx_rate_date: str | None = None
    fx_source: str | None = None
    monthly_history: list = Field(default_factory=list)
    fetched_at: str | None = None
    fresh_until: str | None = None
    mapping_status: str
    cost: float | None = None
    commercial_metrics: dict | None = None


class KeywordMetricsResearchResponse(BaseModel):
    batch_id: str
    status: str
    provider: str
    submitted_count: int
    mapped_count: int
    unmapped_count: int
    provider_requests: int
    results: list[KeywordMetricResultOut]


class KeywordMetricsHandoffRequest(BaseModel):
    evidence_ids: list[str] = Field(min_length=1)
    validation_profile: ValidationProfile = Field(default_factory=ValidationProfile)


class KeywordMetricsHandoffResponse(BaseModel):
    handoff_ids: list[str]
    evidence_ids: list[str]
    selected_count: int
    provider_requests: int = 0
    new_count: int = 0
    existing_count: int = 0
    existing_evidence_ids: list[str] = Field(default_factory=list)
    new_handoff_ids: list[str] = Field(default_factory=list)
    existing_handoff_ids: list[str] = Field(default_factory=list)
    all_handoff_ids: list[str] = Field(default_factory=list)

class KeywordMetricsHandoffOut(BaseModel):
    handoff_id: str
    evidence_id: str
    keyword: str
    search_volume: int | None
    country_code: str
    location_target: dict
    language_code: str
    provider: str
    provider_keyword: str | None = None
    validation_profile: dict
    created_at: datetime
    status: str
    validation_scope: str
    scope_reason: str
    location_status: str
    population_applicability: str
    serp_mode: str
    readiness_status: str


```

# FILE: backend/app/services/run_pipeline.py

```python
Exit code: 0
Wall time: 2.7 seconds
Output:
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import (
    AuthorityEvidence, CandidateEntity, CandidateEvent, CandidateStatus, City, ProjectCandidate,
    ProviderCache, ProviderCall, Run, RunCandidate, RunCandidateAuthorityEvidence,
    SearchVolumeEvidence, KeywordMetricEvidence, KeywordDifficultyEvidence, SerpResultRow, SerpSnapshot, PopulationEvidence,
)
from app.providers.contracts import AuthorityResult, AuthorityTarget, KeywordMetricRequest, SerpRequest
from app.providers.factory import authority_provider, search_volume_provider, serp_provider
from app.services.cache_keys import evidence_is_fresh, provider_cache_key
from app.services.gates import population_gate, search_volume_gate
from app.services.normalization import root_domain
from app.domain.freshness import FreshnessPolicy, can_reuse
from app.services.authority_evaluation import AuthorityEvaluationMode, evaluate_authority, evaluate_general_opportunity


def utc_now() -> datetime:
    """Return naive UTC for compatibility with the existing SQLite DateTime columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _event(db, rc, event_type, previous=None, resulting=None, reason=None, refs=None, metadata=None):
    db.add(CandidateEvent(
        run_id=rc.run_id, run_candidate_id=rc.id, project_candidate_id=rc.project_candidate_id,
        event_type=event_type, previous_status=previous, resulting_status=resulting,
        reason_code=reason, evidence_references=refs or {}, metadata_json=metadata or {},
    ))


def _call(db, run, rc, provider, stage, operation, key, outcome, source_kind, cache_hit=False, cost=0.0):
    db.add(ProviderCall(
        run_id=run.id, run_candidate_id=rc.id, provider=provider, stage=stage,
        operation=operation, request_cache_key=key, outcome=outcome,
        source_kind=source_kind, cache_hit=cache_hit, actual_cost=cost,
        execution_mode=(run.configuration_snapshot or {}).get("dataforseo_mode") if provider.startswith("dataforseo") else None,
    ))


def _set_status(rc, status, reason=None):
    rc.status = status
    if reason:
        rc.reason_codes = list(dict.fromkeys((rc.reason_codes or []) + [reason]))


def _fresh_cached(db: Session, key: str, evidence_type: str, model):
    cache = db.scalar(select(ProviderCache).where(ProviderCache.cache_key == key))
    if not cache or cache.evidence_type != evidence_type or not evidence_is_fresh(cache.fresh_until):
        return None
    evidence = db.get(model, cache.evidence_id)
    return evidence if evidence else None


def _policy_cached(db: Session, key: str, evidence_type: str, model, policy: str):
    """Return compatible evidence plus a stale-warning flag under run policy."""
    cache = db.scalar(select(ProviderCache).where(ProviderCache.cache_key == key))
    if not cache or cache.evidence_type != evidence_type:
        return None, False
    fresh = evidence_is_fresh(cache.fresh_until)
    reuse, warning = can_reuse(policy, fresh)
    evidence = db.get(model, cache.evidence_id) if reuse else None
    return (evidence, warning) if evidence else (None, False)


async def execute_run(db: Session, run_id: str, project_candidate_ids: list[str] | None = None) -> Run:
    run = db.get(Run, run_id)
    if not run:
        raise ValueError("Run not found")
    if run.status == "COMPLETED":
        return run
    run.status = "RUNNING"
    run.started_at = run.started_at or utc_now()
    db.flush()
    stmt = select(ProjectCandidate).where(ProjectCandidate.project_id == run.project_id)
    if project_candidate_ids:
        stmt = stmt.where(ProjectCandidate.id.in_(project_candidate_ids))
    candidates = db.scalars(stmt).all()
    counters = {"total_selected": len(candidates), "population_passed": 0, "population_rejected": 0,
                "sv_passed": 0, "sv_rejected": 0, "serp_ready": 0, "serp_incomplete": 0,
                "authority_completed": 0, "authority_incomplete": 0, "primary_passed": 0,
                "primary_rejected": 0, "provider_errors": 0, "cache_hits": 0, "provider_calls": 0}
    for pc in candidates:
        rc = db.scalar(select(RunCandidate).where(RunCandidate.run_id == run.id, RunCandidate.project_candidate_id == pc.id))
        if not rc:
            rc = RunCandidate(run_id=run.id, project_candidate_id=pc.id, validation_scope=pc.validation_scope)
            db.add(rc); db.flush(); _event(db, rc, "RUN_CANDIDATE_STARTED", resulting=rc.status)
        if rc.finished_at:
            continue
        try:
            result = None
            entity_city = db.scalar(select(City).join(CandidateEntity, City.id == CandidateEntity.city_id).where(CandidateEntity.id == pc.candidate_entity_id))
            is_general = pc.validation_scope == "GENERAL_NICHE"
            if entity_city is None and not is_general:
                _set_status(rc, "ERROR_TERMINAL", "PROVIDER_ERROR"); counters["provider_errors"] += 1; continue
            location_name = f"{entity_city.name}, {entity_city.state_code}" if entity_city else run.country_code
            if not is_general:
                pop_key = provider_cache_key("local", "population", city_id=entity_city.id, vintage=entity_city.population_vintage)
                pop = _fresh_cached(db, pop_key, "population", PopulationEvidence)
                if not pop:
                    pop = PopulationEvidence(candidate_entity_id=pc.candidate_entity_id, city_id=entity_city.id, provider="local", source_kind="census_csv", population=entity_city.population, population_vintage=entity_city.population_vintage, raw_payload={"city": entity_city.name}, source_metadata={"city_id": entity_city.id}, fetched_at=utc_now(), fresh_until=utc_now()+timedelta(days=365))
                    db.add(pop); db.flush(); db.add(ProviderCache(cache_key=pop_key, provider="local", operation="population", evidence_type="population", evidence_id=pop.id, fetched_at=pop.fetched_at, fresh_until=pop.fresh_until))
                rc.population_evidence_id = pop.id; _event(db, rc, "POPULATION_SELECTED", refs={"population_evidence_id": pop.id})
                decision = population_gate(pop.population, type("Profile", (), {"population_enabled": True, "min_population": run.min_population, "max_population": run.max_population})())
                if not decision.passed:
                    _set_status(rc, "POPULATION_REJECTED", decision.reason_codes[0]); counters["population_rejected"] += 1; rc.finished_at = utc_now(); continue
                counters["population_passed"] += 1; _event(db, rc, "POPULATION_PASSED", resulting="SV_PENDING")
            else:
                _event(db, rc, "POPULATION_NOT_APPLICABLE", resulting="SV_PENDING", metadata={"reason": "General Niche candidates are not city-targeted."})
            keyword = pc.display_keyword
            sv_key = provider_cache_key("mock", "search_volume", keyword=keyword, location=location_name, language=run.language_code, country=run.country_code)
            # Search Volume handoffs point to the immutable keyword-metrics
            # evidence row. Keep the legacy SearchVolumeEvidence cache fallback
            # for older project candidates, but prefer the linked handoff row.
            sv = db.get(KeywordMetricEvidence, pc.search_volume_evidence_id) if pc.search_volume_evidence_id else None
            if sv and (sv.submitted_keyword.strip().casefold() != keyword.strip().casefold() or sv.country_code != run.country_code or sv.language_code != run.language_code):
                sv = None
            sv_stale_warning = False
            if sv is None:
                sv, sv_stale_warning = _policy_cached(db, sv_key, "search_volume", SearchVolumeEvidence, run.freshness_policy)
            if sv:
                counters["cache_hits"] += 1; _call(db, run, rc, sv.provider, "sv", "reuse", sv_key, "cache_hit", sv.source_kind, True)
                if sv_stale_warning: _event(db, rc, "STALE_EVIDENCE_REUSED", refs={"search_volume_evidence_id": sv.id}, metadata={"freshness_policy": run.freshness_policy, "stage": "search_volume"})
            else:
                result = (await search_volume_provider().fetch([KeywordMetricRequest(keyword, location_name, run.language_code)]))[0]
                sv = SearchVolumeEvidence(candidate_entity_id=pc.candidate_entity_id, keyword=keyword, location_name=location_name, language_code=run.language_code, country_code=run.country_code, provider=result.provider, source_kind=result.provider, avg_monthly_searches=result.avg_monthly_searches, cpc=result.cpc, competition=result.competition, monthly_history=result.monthly_history, raw_payload=result.raw or {}, request_metadata={"location": location_name}, fetched_at=utc_now(), fresh_until=utc_now()+timedelta(days=30))
                db.add(sv); db.flush(); db.add(ProviderCache(cache_key=sv_key, provider=sv.provider, operation="search_volume", evidence_type="search_volume", evidence_id=sv.id, fetched_at=sv.fetched_at, fresh_until=sv.fresh_until)); _call(db, run, rc, sv.provider, "sv", "fetch", sv_key, "success", sv.source_kind); counters["provider_calls"] += 1
            rc.search_volume_evidence_id = sv.id; _event(db, rc, "SV_SELECTED", refs={"search_volume_evidence_id": sv.id})
            if sv.avg_monthly_searches is None:
                _set_status(rc, "SV_REJECTED", "SV_MISSING"); counters["sv_rejected"] += 1; rc.finished_at = utc_now(); continue
            if sv.avg_monthly_searches < run.min_search_volume:
                _set_status(rc, "SV_REJECTED", "SV_BELOW_THRESHOLD"); counters["sv_rejected"] += 1; rc.finished_at = utc_now(); continue
            counters["sv_passed"] += 1; _event(db, rc, "SV_PASSED", resulting="SERP_PENDING")
            serp_key = provider_cache_key("mock", "serp", keyword=keyword, location=location_name, language=run.language_code, country=run.country_code, device="desktop")
            snap, serp_stale_warning = _policy_cached(db, serp_key, "serp", SerpSnapshot, run.freshness_policy)
            if snap and snap.requested_depth >= run.organic_depth:
                rows = db.scalars(select(SerpResultRow).where(SerpResultRow.snapshot_id == snap.id).order_by(SerpResultRow.position)).all()
                counters["cache_hits"] += 1; _call(db, run, rc, snap.provider, "serp", "reuse", serp_key, "cache_hit", snap.source_kind, True)
                if serp_stale_warning: _event(db, rc, "STALE_EVIDENCE_REUSED", refs={"serp_snapshot_id": snap.id}, metadata={"freshness_policy": run.freshness_policy, "stage": "serp"})
            else:
                serp = (await serp_provider().fetch([SerpRequest(keyword, location_name, run.language_code, run.organic_depth, run.country_code, 2840 if is_general and run.country_code == "US" else None)]))[0]
                provider_status = (serp.raw or {}).get("response", {}).get("status_code")
                if provider_status not in (None, 20000):
                    _call(db, run, rc, serp.provider, "serp", "fetch", serp_key, "error", serp.provider, False)
                    _set_status(rc, "ERROR_RETRYABLE", "SERP_PROVIDER_REQUEST_ERROR")
                    counters["provider_errors"] += 1
                    rc.finished_at = utc_now()
                    db.add(CandidateEvent(run_id=run.id, run_candidate_id=rc.id, project_candidate_id=pc.id, event_type="SERP_PROVIDER_ERROR", resulting_status=rc.status, reason_code="SERP_PROVIDER_REQUEST_ERROR", metadata_json={"provider_status_code": provider_status, "provider_status_message": (serp.raw or {}).get("response", {}).get("status_message")}))
                    continue
                snap = SerpSnapshot(candidate_id="pipeline", candidate_entity_id=pc.candidate_entity_id, provider=serp.provider, source_kind=serp.provider, keyword=keyword, location_name=location_name, language_code=run.language_code, country_code=run.country_code, requested_depth=run.organic_depth, raw_payload=serp.raw or {}, fetched_at=utc_now(), fresh_until=utc_now()+timedelta(days=7))
                db.add(snap); db.flush(); db.add(ProviderCache(cache_key=serp_key, provider=snap.provider, operation="serp", evidence_type="serp", evidence_id=snap.id, fetched_at=snap.fetched_at, fresh_until=snap.fresh_until)); _call(db, run, rc, snap.provider, "serp", "fetch", serp_key, "success", snap.source_kind); counters["provider_calls"] += 1
                rows=[]
                for item in serp.organic[:run.organic_depth]:
                    row=SerpResultRow(snapshot_id=snap.id, position=item.position, title=item.title, url=item.url, root_domain=root_domain(item.url)); db.add(row); rows.append(row)
                db.flush()
            rc.serp_snapshot_id = snap.id; _event(db, rc, "SERP_SELECTED", refs={"serp_snapshot_id": snap.id})
            if len(rows) < run.organic_depth:
                _set_status(rc, "ERROR_RETRYABLE", "SERP_INSUFFICIENT_ORGANIC_RESULTS"); counters["serp_incomplete"] += 1; rc.finished_at = utc_now(); continue
            rows = rows[:run.organic_depth]; counters["serp_ready"] += 1; _event(db, rc, "SERP_READY", resulting="AUTHORITY_PENDING")
            metrics=[]; metric_sources=[]; missing=[]
            for row in rows:
                authority_key = provider_cache_key("mock", "authority", target_url=row.url, root_domain=row.root_domain, target_type="URL")
                cached, stale_warning = _policy_cached(db, authority_key, "authority", AuthorityEvidence, run.freshness_policy)
                if cached:
                    metrics.append(AuthorityResult(row.url, row.root_domain, cached.da, cached.pa, cached.spam_score, cached.linking_root_domains, cached.backlinks, cached.provider, cached.raw_payload)); metric_sources.append((cached, stale_warning, authority_key))
                else:
                    metrics.append(None); metric_sources.append((None, False, authority_key)); missing.append(AuthorityTarget(row.url, row.root_domain))
            # ADAPTIVE authority is deliberately acquired as ordered batches.  A
            # normal full run still requests the complete unresolved set in one
            # batch; recalculation therefore never falls through to eager depth.
            fetched_queue = []
            unresolved_index = 0
            adaptive_recalculation = run.run_type == "RECALCULATION" and run.authority_evaluation_mode == "ADAPTIVE"
            batch_size = max(1, run.authority_batch_size) if adaptive_recalculation else max(1, len(missing))
            available=0; low=0
            fetched_count = 0
            observed_metrics = list(metrics)
            for row_index, (row, metric, source) in enumerate(zip(rows, metrics, metric_sources)):
                cached, stale_warning, authority_key = source
                if metric is None:
                    if not fetched_queue:
                        batch = missing[unresolved_index:unresolved_index + batch_size]
                        unresolved_index += len(batch)
                        fetched_queue = list(await authority_provider().fetch(batch))
                        fetched_count += len(fetched_queue)
                        counters["provider_calls"] += 1
                        if fetched_queue:
                            _call(db, run, rc, fetched_queue[0].provider, "authority", "batch_fetch", f"batch:{unresolved_index // batch_size}", "success", fetched_queue[0].provider)
                    metric = fetched_queue.pop(0)
                    observed_metrics[row_index] = metric
                    ev=AuthorityEvidence(candidate_entity_id=pc.candidate_entity_id, target_url=row.url, root_domain=row.root_domain, target_type="URL", provider=metric.provider, source_kind=metric.provider, da=metric.da, pa=metric.pa, spam_score=metric.spam_score, linking_root_domains=metric.linking_root_domains, backlinks=metric.backlinks, raw_payload=metric.raw or {}, fetched_at=utc_now(), fresh_until=utc_now()+timedelta(days=30)); db.add(ev); db.flush(); db.add(ProviderCache(cache_key=authority_key, provider=ev.provider, operation="authority", evidence_type="authority", evidence_id=ev.id, fetched_at=ev.fetched_at, fresh_until=ev.fresh_until)); counters["provider_calls"] += 1
                else:
                    ev = cached; _call(db, run, rc, ev.provider, "authority", "reuse", authority_key, "cache_hit", ev.source_kind, True); counters["cache_hits"] += 1
                    if stale_warning: _event(db, rc, "STALE_EVIDENCE_REUSED", refs={"authority_evidence_id": ev.id}, metadata={"freshness_policy": run.freshness_policy, "stage": "authority"})
                usable=metric.da is not None; available += int(usable); counted=bool(usable and metric.da < run.da_threshold); low += int(counted); db.add(RunCandidateAuthorityEvidence(run_candidate_id=rc.id, serp_result_row_id=row.id, authority_evidence_id=ev.id, ranking_position=row.position, da_value_used=metric.da, counted_as_low_da=counted))
                if adaptive_recalculation:
                    probe = evaluate_authority([m.da if m else None for m in observed_metrics], run.organic_depth, run.required_low_da_count, run.ideal_weak_domains, run.da_threshold, AuthorityEvaluationMode.ADAPTIVE, run.adaptive_seek_ideal, row_index + 1, fetched_count)
                    if probe.primary_gate_result in ("PASS", "PRIMARY_REJECTED"):
                        break
            if adaptive_recalculation:
                # Positions after the stopping point are intentionally unchecked,
                # even when compatible cache rows existed for them.
                evaluated_positions = row_index + 1 if rows else 0
                metrics = observed_metrics[:evaluated_positions] + [None] * max(0, len(rows) - evaluated_positions)
            minimum_weak = run.required_low_da_count
            evaluation = evaluate_authority([metric.da if metric else None for metric in metrics], run.organic_depth, minimum_weak, run.ideal_weak_domains, run.da_threshold, AuthorityEvaluationMode(run.authority_evaluation_mode), run.adaptive_seek_ideal, sum(1 for source in metric_sources if source[0] is not None), len(missing))
            general_opportunity = evaluate_general_opportunity([metric.da if metric else None for metric in metrics], 20.0) if is_general else None
            rc.organic_results_evaluated=len(rows); rc.authority_results_available=available; rc.low_da_count=evaluation.confirmed_weak_count; rc.da_threshold_used=run.da_threshold; rc.required_low_da_count_used=minimum_weak; rc.minimum_weak_domains_used=minimum_weak; rc.ideal_weak_domains_used=run.ideal_weak_domains; rc.authority_evaluation_mode_used=run.authority_evaluation_mode; rc.adaptive_seek_ideal_used=run.adaptive_seek_ideal; rc.authority_targets_evaluated=evaluation.authority_targets_evaluated; rc.authority_targets_cached=evaluation.authority_targets_cached; rc.authority_targets_fetched=evaluation.authority_targets_fetched; rc.authority_targets_unchecked=evaluation.unchecked_remaining; rc.confirmed_weak_count=evaluation.confirmed_weak_count; rc.opportunity_classification=evaluation.opportunity_classification
            if general_opportunity:
                rc.low_da_count = general_opportunity.weak_count; rc.da_threshold_used = general_opportunity.threshold; rc.opportunity_classification = general_opportunity.classification; rc.authority_opportunity_reason = general_opportunity.reason
            authority_complete = available == len(rows) or (adaptive_recalculation and evaluation.primary_gate_result != "ERROR_RETRYABLE")
            if not authority_complete:
                _set_status(rc, "ERROR_RETRYABLE", "DATA_INCOMPLETE"); counters["authority_incomplete"] += 1
            elif is_general:
                _set_status(rc, "PASS"); rc.automatic_status = general_opportunity.classification if general_opportunity else "POTENTIAL_NICHE"; rc.primary_gate_passed = True; counters["primary_passed"] += 1
            elif low < minimum_weak:
                _set_status(rc, "PRIMARY_REJECTED", "LOW_DA_COUNT_BELOW_REQUIRED"); rc.automatic_status="PRIMARY_REJECTED"; rc.primary_gate_passed=False; counters["primary_rejected"] += 1
            else:
                _set_status(rc, "PASS"); rc.automatic_status="PASS"; rc.primary_gate_passed=True; counters["primary_passed"] += 1
            # KD is evaluated only after the DA primary gate. It remains a
            # supporting signal and can never turn a DA failure into a pass.
            if run.kd_enabled:
                kd_key = provider_cache_key(sv.provider, "keyword_difficulty", keyword=keyword, location=location_name, language=run.language_code, country=run.country_code)
                kd, kd_stale_warning = _policy_cached(db, kd_key, "keyword_difficulty", KeywordDifficultyEvidence, run.freshness_policy)
                if kd and run.kd_provider == "moz" and kd.provider not in ("moz", "moz_csv", "mock"):
                    kd = None; kd_stale_warning = False
                if kd and run.kd_provider == "ahrefs" and kd.provider not in ("ahrefs", "ahrefs_csv"):
                    kd = None; kd_stale_warning = False
                if not kd and result is not None and result.keyword_difficulty is not None:
                    kd = KeywordDifficultyEvidence(candidate_entity_id=pc.candidate_entity_id, keyword=keyword, location_name=location_name, language_code=run.language_code, country_code=run.country_code, provider=sv.provider, metric_type="keyword_difficulty", difficulty=result.keyword_difficulty, source_kind=sv.source_kind, raw_payload=result.raw or {}, request_metadata={"shared_with_search_volume": True}, fetched_at=utc_now(), fresh_until=utc_now()+timedelta(days=30))
                    db.add(kd); db.flush(); db.add(ProviderCache(cache_key=kd_key, provider=kd.provider, operation="keyword_difficulty", evidence_type="keyword_difficulty", evidence_id=kd.id, fetched_at=kd.fetched_at, fresh_until=kd.fresh_until))
                if kd:
                    rc.keyword_difficulty_evidence_id = kd.id; rc.kd_value_used = kd.difficulty; rc.kd_status = "IDEAL" if kd.difficulty < run.kd_threshold else "ABOVE_PREFERRED"
                    if kd_stale_warning: _event(db, rc, "STALE_EVIDENCE_REUSED", refs={"keyword_difficulty_evidence_id": kd.id}, metadata={"freshness_policy": run.freshness_policy, "stage": "keyword_difficulty"})
                    if rc.primary_gate_passed and run.kd_mode == "HARD_GATE" and kd.difficulty >= run.kd_threshold:
                        _set_status(rc, "PRIMARY_REJECTED", "KD_ABOVE_THRESHOLD"); rc.automatic_status="PRIMARY_REJECTED"; rc.primary_gate_passed=False; counters["primary_rejected"] += 1
            counters["authority_completed"] += int(available == len(rows)); _event(db, rc, "PRIMARY_GATE_PASSED" if rc.primary_gate_passed else "PRIMARY_GATE_REJECTED", resulting=rc.status, metadata={"low_da_count": low, "available": available}); rc.finished_at=utc_now(); pc.current_status=rc.status; pc.automatic_status=rc.automatic_status; pc.current_reason_codes=rc.reason_codes; pc.latest_run_id=run.id
        except Exception as exc:
            _set_status(rc, "ERROR_RETRYABLE", "PROVIDER_ERROR"); counters["provider_errors"] += 1; rc.finished_at=utc_now(); db.add(CandidateEvent(run_id=run.id, run_candidate_id=rc.id, project_candidate_id=pc.id, event_type="EXECUTION_ERROR", resulting_status=rc.status, reason_code="PROVIDER_ERROR", metadata_json={"error": str(exc)}))
        db.flush()
    run.counters = counters; run.status="COMPLETED"; run.finished_at=utc_now(); db.commit(); db.refresh(run); return run


```

# FILE: backend/alembic/versions/c15_project_candidate_sv_evidence.py

```python
Exit code: 0
Wall time: 2.3 seconds
Output:
"""link project candidates to immutable search-volume evidence"""
from alembic import op
import sqlalchemy as sa

revision = "c15projectcandidatesvevidence"
down_revision = "c13userquotas"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("project_candidates", recreate="always") as batch_op:
        batch_op.add_column(sa.Column("search_volume_evidence_id", sa.String(), nullable=True))
        batch_op.create_index("ix_project_candidates_search_volume_evidence_id", ["search_volume_evidence_id"])
        batch_op.create_foreign_key("fk_project_candidates_search_volume_evidence", "keyword_metric_evidence", ["search_volume_evidence_id"], ["id"])


def downgrade():
    with op.batch_alter_table("project_candidates", recreate="always") as batch_op:
        batch_op.drop_constraint("fk_project_candidates_search_volume_evidence", type_="foreignkey")
        batch_op.drop_index("ix_project_candidates_search_volume_evidence_id")
        batch_op.drop_column("search_volume_evidence_id")


```

# FILE: backend/alembic/versions/f2_two_pipeline_scope.py

```python
Exit code: 0
Wall time: 2.2 seconds
Output:
"""add explicit local/general validation scope fields"""
from alembic import op
import sqlalchemy as sa

revision = "f2twopipelinescope"
down_revision = "c15projectcandidatesvevidence"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("candidate_entities", recreate="always") as batch:
        batch.alter_column("city_id", existing_type=sa.String(), nullable=True)
        batch.add_column(sa.Column("validation_scope", sa.String(30), nullable=False, server_default="LOCAL_RANK_RENT"))
        batch.create_index("ix_candidate_entities_validation_scope", ["validation_scope"])
    with op.batch_alter_table("project_candidates", recreate="always") as batch:
        batch.add_column(sa.Column("validation_scope", sa.String(30), nullable=False, server_default="LOCAL_RANK_RENT"))
        batch.add_column(sa.Column("scope_reason", sa.String(500), nullable=True))
        batch.create_index("ix_project_candidates_validation_scope", ["validation_scope"])
    with op.batch_alter_table("run_candidates", recreate="always") as batch:
        batch.add_column(sa.Column("validation_scope", sa.String(30), nullable=False, server_default="LOCAL_RANK_RENT"))
        batch.add_column(sa.Column("authority_opportunity_reason", sa.String(1000), nullable=True))
        batch.create_index("ix_run_candidates_validation_scope", ["validation_scope"])


def downgrade():
    with op.batch_alter_table("run_candidates", recreate="always") as batch:
        batch.drop_index("ix_run_candidates_validation_scope")
        batch.drop_column("authority_opportunity_reason")
        batch.drop_column("validation_scope")
    with op.batch_alter_table("project_candidates", recreate="always") as batch:
        batch.drop_index("ix_project_candidates_validation_scope")
        batch.drop_column("scope_reason")
        batch.drop_column("validation_scope")
    with op.batch_alter_table("candidate_entities", recreate="always") as batch:
        batch.drop_index("ix_candidate_entities_validation_scope")
        batch.drop_column("validation_scope")
        batch.alter_column("city_id", existing_type=sa.String(), nullable=False)


```

# FILE: frontend/app/research/search-volume/page.tsx

```tsx
Exit code: 0
Wall time: 2.2 seconds
Output:
"use client";

import { ChangeEvent, FormEvent, useRef, useState } from "react";
import { AppShell } from "../../components/AppShell";
import { formatUsd } from "../../../lib/formatCurrency";
import "./search-volume.css";
import "./search-volume-layout.css";
import "./commercial-insights.css";

const API = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000/api/v1";
type Month = { year: number; month: number; searches: number };
type Projected = { ctr: number; clicks: number | null; traffic_value: number | null };
type Result = { id?: string | null; submitted_keyword: string; provider_keyword?: string | null; mapping_status?: string; avg_monthly_searches?: number | null; competition?: number | null; competition_index?: number | null; usd_cpc?: number | null; usd_low_bid?: number | null; usd_high_bid?: number | null; monthly_history?: Month[]; commercial_metrics?: { commercial_search_value?: number | null; projected?: Record<string, Projected> } | null };
const countries = ["WORLD", "US", "GB", "PK", "CA", "AU", "AE", "DE", "IN", "FR", "JP", "BR", "ZA"];
const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const countryName = (code: string) => code === "WORLD" ? "Global / Worldwide" : new Intl.DisplayNames(["en"], { type: "region" }).of(code) || code;
const parseKeywords = (value: string) => [...new Map(value.split(/\r?\n/).map(x => x.trim()).filter(Boolean).map(x => [x.toLowerCase(), x])).values()];
const competition = (value?: number | null) => value === 2 ? "Low" : value === 3 ? "Medium" : value === 4 ? "High" : value === 0 ? "Unspecified" : "Unknown";

export default function SearchVolume() {
  const [text, setText] = useState("");
  const [country, setCountry] = useState("US");
  const [results, setResults] = useState<Result[]>([]);
  const [filter, setFilter] = useState("");
  const [order, setOrder] = useState<"asc" | "desc">("desc");
  const [threshold, setThreshold] = useState(260);
  const [selected, setSelected] = useState<string[]>([]);
  const [open, setOpen] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [handoff, setHandoff] = useState<{ newCount: number; existingCount: number; allIds: string[] } | null>(null);
  const input = useRef<HTMLInputElement>(null);
  const keywords = parseKeywords(text);
  const mapped = results.filter(result => result.mapping_status !== "UNMAPPED");
  const qualifying = results.filter(result => result.id && result.avg_monthly_searches != null && result.avg_monthly_searches >= threshold);
  const median = (values: Array<number | null | undefined>) => {
    const sorted = values.filter((value): value is number => typeof value === "number").sort((a, b) => a - b);
    return sorted.length ? sorted[Math.floor(sorted.length / 2)] : null;
  };
  const visible = [...results].filter(result => !filter || result.submitted_keyword.toLowerCase().includes(filter.toLowerCase())).sort((a, b) => a.avg_monthly_searches == null ? 1 : b.avg_monthly_searches == null ? -1 : order === "asc" ? a.avg_monthly_searches - b.avg_monthly_searches : b.avg_monthly_searches - a.avg_monthly_searches);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!keywords.length) { setMessage("Enter at least one keyword."); return; }
    setLoading(true); setMessage("");
    try {
      const token = sessionStorage.getItem("nicheforge_access_token");
      const target = country === "WORLD" ? { country_code: "WORLD", target_type: "WORLDWIDE" } : { country_code: country };
      const response = await fetch(`${API}/keyword-metrics/research`, { method: "POST", headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) }, body: JSON.stringify({ keywords, target: { location_name: countryName(country), location_target: target, language_code: "en", country_code: country }, provider: "google_ads" }) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Search-volume research failed");
      setResults(data.results || []);
    } catch (error) { setMessage(error instanceof Error ? error.message : "Search-volume research failed"); }
    finally { setLoading(false); }
  }

  function importKeywords(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]; if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const values = String(reader.result || "").split(/\r?\n/).map(x => x.trim()).filter(Boolean).map(x => x.split(",")[0].replace(/^"|"$/g, ""));
      const unique = [...new Map(values.filter(x => x.toLowerCase() !== "keyword").map(x => [x.toLowerCase(), x])).values()];
      setText(unique.join("\n")); setMessage(`Imported ${unique.length} unique keywords.`);
    };
    reader.readAsText(file); event.target.value = "";
  }

  function copy(full: boolean) {
    const values = visible.map(result => full ? [result.submitted_keyword, result.provider_keyword, result.mapping_status, result.avg_monthly_searches ?? "", result.usd_cpc ?? "", result.usd_low_bid ?? "", result.usd_high_bid ?? ""].join("\t") : `${result.submitted_keyword}\t${result.avg_monthly_searches ?? ""}`);
    navigator.clipboard?.writeText(values.join("\n")); setMessage(`Copied ${values.length} rows.`);
  }

  function exportCsv() {
    const rows = visible.map(result => [result.submitted_keyword, result.provider_keyword, result.mapping_status, result.avg_monthly_searches, result.usd_cpc, result.usd_low_bid, result.usd_high_bid].map(value => `"${String(value ?? "").replaceAll('"', '""')}"`).join(","));
    const link = document.createElement("a"); link.href = URL.createObjectURL(new Blob([["Keyword,Provider Keyword,Mapping Status,SV,CPC USD,Low Bid USD,High Bid USD", ...rows].join("\n")], { type: "text/csv" })); link.download = "nicheforge-search-volume.csv"; link.click();
  }

  async function send() {
    const ids = selected.length ? selected : qualifying.map(result => result.id!).filter(Boolean); if (!ids.length) return;
    const token = sessionStorage.getItem("nicheforge_access_token");
    const response = await fetch(`${API}/keyword-metrics/send-to-validation`, { method: "POST", headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) }, body: JSON.stringify({ evidence_ids: ids, validation_profile: { min_search_volume: threshold } }) });
    const data = await response.json();
    if (!response.ok) { setMessage(data.detail || "Handoff failed"); return; }
    const allIds = Array.isArray(data.all_handoff_ids) ? data.all_handoff_ids : [];
    sessionStorage.setItem("nicheforge_last_handoff_ids", JSON.stringify(allIds));
    setHandoff({ newCount: data.new_count || 0, existingCount: data.existing_count || 0, allIds });
    window.location.assign(allIds.length === 1 ? `/rank-rent/validator?handoff_id=${encodeURIComponent(allIds[0])}` : "/rank-rent/validator");
  }

  return <AppShell active="Search Volume">
    <div className="page-head"><div><p className="eyebrow">Research</p><h1>Search Volume Research</h1><p className="muted">Research demand, trends and commercial potential.</p></div><div className="head-actions"><input ref={input} hidden type="file" accept=".txt,.csv" onChange={importKeywords} /><button className="button secondary" onClick={() => input.current?.click()}>Import Keywords</button></div></div>
<form className="card research-form" onSubmit={submit}><div className="top-fields"><label className="keyword-field"><span>Keywords</span><textarea value={text} onChange={event => setText(event.target.value)} rows={4} /><small>{keywords.length} parsed keyword(s)</small></label><label><span>Country</span><select className="country-select" value={country} onChange={event => setCountry(event.target.value)}>{countries.map(code => <option key={code} value={code}>{countryName(code)}</option>)}</select></label><button className="button primary submit-button" disabled={loading}>{loading ? "Researching..." : "Check Search Volume"}</button></div></form>
    {message && <div className="error-banner">{message}</div>}
    {results.length > 0 && <><div className="metric-grid"><Stat title="Results" value={results.length} subtitle={`${mapped.length} mapped / ${results.length - mapped.length} unmapped`} /><Stat title="Median Search Volume" value={median(mapped.map(result => result.avg_monthly_searches))} subtitle="Monthly searches" /><Stat title="12-Month Trend" value={mapped.some(result => result.monthly_history?.length === 12) ? "Available" : "Unavailable"} subtitle="Stored monthly data" /><Stat title="Median Competition" value={median(mapped.map(result => result.competition_index))} subtitle="Google Ads index" /><Stat title="R&R Candidates" value={qualifying.length} subtitle={`${threshold}+ SV`} /></div>{qualifying.length > 0 && <div className="card handoff-banner"><div><h2>Rank &amp; Rent Candidate Handoff</h2><p>{qualifying.length} keyword{qualifying.length === 1 ? "" : "s"} meet the current <strong>{threshold}+ SV</strong> candidate threshold.</p><p className="muted">SERP / DA / KD validation happens only after handoff.</p></div><div className="handoff-controls"><label>Candidate threshold<input type="number" value={threshold} onChange={event => setThreshold(Number(event.target.value) || 0)} /> <span>SV</span></label><button type="button" className="button primary" onClick={send}>Send Qualifying to Rank &amp; Rent</button></div></div>}{handoff && <div className="success-banner"><strong>Sent to Rank &amp; Rent</strong><span>{handoff.newCount} new candidate{handoff.newCount === 1 ? "" : "s"} added.</span><span>{handoff.existingCount} already existed.</span><span>No provider calls were required.</span></div>}<section className="card results-card"><div className="results-toolbar"><input placeholder="Search keyword..." value={filter} onChange={event => setFilter(event.target.value)} /><div className="result-actions"><button type="button" className="button secondary" onClick={() => copy(true)}>Copy Results</button><button type="button" className="button secondary" onClick={() => copy(false)}>Copy SV Only</button><button type="button" className="button secondary" onClick={exportCsv}>Export CSV</button></div></div><div className="table-wrap compact-table"><table className="sv-table"><thead><tr><th>Select</th><th>Keyword</th><th title="Sort by Search Volume" aria-label="Sort by Search Volume" onClick={() => setOrder(order === "asc" ? "desc" : "asc")}>SV {order === "asc" ? "up" : "down"}</th><th>12M Trend</th><th>Competition</th><th>Avg CPC</th><th>Low Bid</th><th>High Bid</th><th>R&amp;R</th></tr></thead><tbody>{visible.map((result, index) => <ResultRow key={`${result.id || result.submitted_keyword}-${index}`} result={result} threshold={threshold} checked={!!result.id && selected.includes(result.id)} onSelect={checked => result.id && setSelected(old => checked ? [...new Set([...old, result.id!])] : old.filter(id => id !== result.id))} expanded={open === result.id} onExpand={() => setOpen(open === result.id ? null : result.id || null)} />)}</tbody></table></div><div className="results-footer">Showing {visible.length} visible / {results.length} submitted / {mapped.length} mapped / {results.length - mapped.length} unmapped</div></section></>}</AppShell>;
}

function Stat({ title, value, subtitle }: { title: string; value: number | string | null; subtitle: string }) { return <div className="metric card"><span className="metric-title">{title}</span><strong>{value == null ? "-" : typeof value === "number" ? value.toLocaleString() : value}</strong><small>{subtitle}</small></div>; }
function ResultRow({ result: r, threshold, checked, onSelect, expanded, onExpand }: { result: Result; threshold: number; checked: boolean; onSelect: (checked: boolean) => void; expanded: boolean; onExpand: () => void }) { const qualifies = !!r.id && r.avg_monthly_searches != null && r.avg_monthly_searches >= threshold; const label = competition(r.competition); return <><tr><td><input type="checkbox" checked={checked} disabled={!qualifies} onChange={event => onSelect(event.target.checked)} /></td><td><button className="row-link" onClick={onExpand} aria-expanded={expanded}>{expanded ? "v" : ">"} {r.submitted_keyword}</button></td><td className="numeric">{r.avg_monthly_searches == null ? "" : r.avg_monthly_searches.toLocaleString()}</td><td><Bars values={r.monthly_history || []} /></td><td><span className={`competition-pill competition-${label.toLowerCase()}`}>{r.competition_index ?? ""} ({label})</span></td><td className="numeric">{formatUsd(r.usd_cpc)}</td><td className="numeric">{formatUsd(r.usd_low_bid)}</td><td className="numeric">{formatUsd(r.usd_high_bid)}</td><td>{qualifies ? <span className="row-status">R&amp;R Candidate</span> : ""}</td></tr>{expanded && <tr className="expanded-row"><td colSpan={9}><div className="expanded-content"><div><h3>Monthly Search Volume</h3><Bars values={r.monthly_history || []} large /></div><aside className="commercial-panel"><h3>Commercial Insights</h3><strong className="commercial-value">{formatUsd(r.commercial_metrics?.commercial_search_value ?? null)}</strong><p className="muted">Commercial Search Value</p><table className="commercial-table"><thead><tr><th>Position</th><th>CTR</th><th>Est. Clicks</th><th>Projected Traffic Value</th></tr></thead><tbody>{["1", "3", "5"].map(position => { const row = r.commercial_metrics?.projected?.[position]; return <tr key={position}><td>#{position}</td><td>{row ? `${Math.round(row.ctr * 100)}%` : ""}</td><td>{row?.clicks == null ? "" : Math.round(row.clicks).toLocaleString()}</td><td>{formatUsd(row?.traffic_value ?? null)}</td></tr>; })}</tbody></table><small>Projected Traffic Value estimates the advertising-equivalent value of modeled organic clicks. It is not projected revenue.</small></aside></div></td></tr>}</>; }
function Bars({ values, large = false }: { values: Month[]; large?: boolean }) { if (!values.length) return <span className="muted">Unavailable</span>; const max = Math.max(...values.map(value => value.searches), 1); return <div className={large ? "trend-bars large" : "trend-bars"}>{values.map(value => <div className="trend-bar-item" tabIndex={0} key={`${value.year}-${value.month}`}><i style={{ height: `${Math.max(value.searches / max * 100, 3)}%` }} /><small>{monthNames[(value.month - 1 + 12) % 12]}</small><span className="trend-tooltip"><strong>{monthNames[(value.month - 1 + 12) % 12]} {value.year}</strong><br />{value.searches.toLocaleString()} searches</span></div>)}</div>; }


```

# FILE: frontend/app/rank-rent/validator/page.tsx

```tsx
Exit code: 0
Wall time: 1.8 seconds
Output:
"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { AppShell } from "../../components/AppShell";
import "./validator.css";

const API = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000/api/v1";
const stages = ["Population", "Search Volume", "SERP", "DA Gate", "Deep Analysis", "KD", "Result"];
const profile = { min_population: 20000, max_population: 120000, min_search_volume: 260, da_threshold: 10, required_low_da_count: 4, ideal_weak_domains: 5, organic_depth: 10, kd_enabled: true, kd_provider: "moz", kd_threshold: 15, kd_mode: "PRIORITY" };
type Handoff = { handoff_id: string; evidence_id: string; keyword: string; search_volume: number | null; provider: string; country_code: string; status: string; validation_scope?: string; location_status?: string; population_applicability?: string; serp_mode?: string; readiness_status?: string };
type AttachOutcome = { handoff_id: string; keyword?: string; status: string; validation_scope?: string; project_candidate_id?: string; city_candidates?: LocationCandidate[]; authority_opportunity?: string; authority_opportunity_reason?: string; weak_site_count?: number; authority_threshold?: number };
type Run = { id: string; project_id: string; status: string; counters: Record<string, unknown>; progress?: number; candidate_results?: Array<{ keyword?: string; validation_scope?: string; population_applicability?: string; serp_mode?: string; authority_opportunity?: string | null; authority_opportunity_reason?: string | null; weak_site_count?: number | null; authority_threshold?: number | null; status: string; reason_codes: string[]; population: string; search_volume: string; search_volume_value?: number | null; search_volume_provider?: string | null; serp: string; serp_reason?: string | null; serp_count?: number; serp_required?: number; serp_evidence?: Array<{ position: number; domain: string; url: string; title?: string }>; da: string; da_evidence?: Array<{ position: number; domain?: string; url?: string; da?: number | null; pa?: number | null; provider?: string | null }>; deep_analysis: string; kd: string; final_result: string }> };
type InitState = "idle" | "setting_up_project" | "attaching_candidate" | "previewing" | "ready" | "location_confirmation_required" | "initialization_error";
type LocationCandidate = { city: string; state: string; city_id: string };
class ApiError extends Error { detail: unknown; constructor(detail: unknown) { super(typeof detail === "string" ? detail : "NicheForge request failed"); this.detail = detail; } }

function headers(): Record<string, string> {
  const token = sessionStorage.getItem("nicheforge_access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request(path: string, init?: RequestInit) {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 15000);
  const response = await fetch(`${API}${path}`, { ...init, signal: controller.signal, headers: { "Content-Type": "application/json", ...headers(), ...(init?.headers || {}) } }).finally(() => window.clearTimeout(timeout));
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new ApiError(data.detail || "NicheForge request failed");
  return data;
}

export default function Validator() {
  const params = useSearchParams();
  const handoffId = params.get("handoff_id") || params.get("handoff");
  const [handoffs, setHandoffs] = useState<Handoff[]>([]);
  const [selected, setSelected] = useState<Handoff | null>(null);
  const [project, setProject] = useState("");
  const [projectId, setProjectId] = useState("");
  const [candidateCount, setCandidateCount] = useState(0);
  const [attached, setAttached] = useState(false);
  const [run, setRun] = useState<Run | null>(null);
  const [preview, setPreview] = useState<Record<string, unknown> | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [errorKind, setErrorKind] = useState("");
  const [initializationFailed, setInitializationFailed] = useState(false);
  const [initState, setInitState] = useState<InitState>("idle");
  const [locationCandidates, setLocationCandidates] = useState<LocationCandidate[]>([]);
  const [locationAmbiguities, setLocationAmbiguities] = useState<Array<{ handoff_id: string; keyword: string; candidates: LocationCandidate[] }>>([]);
  const [selectedLocations, setSelectedLocations] = useState<Record<string, LocationCandidate>>({});
  const [attachOutcomes, setAttachOutcomes] = useState<AttachOutcome[]>([]);
  const initializationStarted = useRef(false);

  useEffect(() => {
    const path = handoffId ? `/rank-rent/handoffs/${encodeURIComponent(handoffId)}` : "/rank-rent/handoffs";
    fetch(`${API}${path}`, { headers: headers() })
      .then(async response => { if (!response.ok) throw new Error(); return response.json(); })
      .then(data => { const list = (Array.isArray(data) ? data : [data]) as Handoff[]; setHandoffs(list); setSelected(list[0] || null); })
      .catch(() => { if (handoffId) showError("The requested Search Volume handoff could not be found.", "API ERROR"); });
  }, [handoffId]);

  useEffect(() => {
    if (!handoffs.length || initializationStarted.current) return;
    initializationStarted.current = true;
    void initialize(handoffs);
  }, [handoffs]);

  const progress = useMemo(() => {
    if (!run) return 0;
    if (typeof run.progress === "number") return run.progress;
    const total = Number(run.counters?.total_selected || run.counters?.total || 0);
    const complete = Number(run.counters?.completed || run.counters?.complete || run.counters?.processed || 0);
    return total ? Math.min(100, Math.round(complete / total * 100)) : run.status === "COMPLETED" ? 100 : 0;
  }, [run]);

  function showError(message: string, kind = "ERROR") { setError(message); setErrorKind(kind); }

  async function initialize(importedHandoffs: Handoff[]) {
    setBusy(true); setError(""); setInitializationFailed(false); setInitState("setting_up_project");
    try {
      let resolvedProjectId = sessionStorage.getItem("nicheforge_current_project_id");
      if (resolvedProjectId) {
        try {
          await request(`/projects/${encodeURIComponent(resolvedProjectId)}/validation-preview`, { method: "POST", body: JSON.stringify({ profile, candidate_ids: [] }) });
        } catch (cause) {
          if (cause instanceof Error && /404|not found/i.test(cause.message)) {
            sessionStorage.removeItem("nicheforge_current_project_id");
            resolvedProjectId = null;
          } else if (cause instanceof Error && cause.name === "AbortError") throw cause;
        }
      }
      if (!resolvedProjectId) {
        const created = await request("/projects", { method: "POST", body: JSON.stringify({ name: project || "Rank & Rent Project", profile }) });
        resolvedProjectId = created.id;
      }
      if (!resolvedProjectId) throw new Error("Project creation returned no project ID.");
      const finalProjectId = resolvedProjectId;
      sessionStorage.setItem("nicheforge_current_project_id", finalProjectId);
      setProjectId(finalProjectId);
      setInitState("attaching_candidate");
      const attachedResult = await request(`/projects/${encodeURIComponent(finalProjectId)}/handoffs/attach`, { method: "POST", body: JSON.stringify({ handoff_ids: importedHandoffs.map(item => item.handoff_id) }) });
      const count = Number(attachedResult.created_count || 0) + Number(attachedResult.existing_count || 0);
      if (count < 1 || !attachedResult.project_candidate_ids?.length) throw new Error("The handoff did not produce an executable ProjectCandidate.");
      setCandidateCount(count); setAttached(true);
      setAttachOutcomes((attachedResult.results || []) as AttachOutcome[]);
      const pending = (attachedResult.results || []).filter((item: { status?: string }) => item.status === "LOCAL_LOCATION_REQUIRED");
      if (pending.length) setLocationAmbiguities(pending.map((item: { handoff_id: string; keyword: string; city_candidates?: LocationCandidate[] }) => ({ handoff_id: item.handoff_id, keyword: item.keyword, candidates: item.city_candidates || [] })));
      setInitState("previewing");
      const previewData = await request(`/projects/${encodeURIComponent(finalProjectId)}/validation-preview`, { method: "POST", body: JSON.stringify({ profile, candidate_ids: attachedResult.project_candidate_ids }) });
      setPreview(previewData); setInitState(pending.length ? "location_confirmation_required" : "ready");
    } catch (cause) {
      if (cause instanceof ApiError && typeof cause.detail === "object" && cause.detail && ["HANDOFF_CITY_AMBIGUOUS", "HANDOFF_CITY_UNRESOLVED"].includes((cause.detail as { code?: string }).code || "") && (((cause.detail as { candidates?: LocationCandidate[] }).candidates || []).length > 0 || ((cause.detail as { ambiguities?: unknown[] }).ambiguities || []).length > 0)) {
        const detail = cause.detail as { candidates?: LocationCandidate[]; ambiguities?: Array<{ handoff_id: string; keyword: string; candidates: LocationCandidate[] }> };
        setLocationCandidates(detail.candidates || []);
        setLocationAmbiguities(detail.ambiguities || (detail.candidates ? [{ handoff_id: handoffs[0]?.handoff_id || "", keyword: handoffs[0]?.keyword || "", candidates: detail.candidates }] : []));
        setInitState("location_confirmation_required");
        setErrorKind("LOCATION CONFIRMATION REQUIRED");
        setError("");
        return;
      }
      setInitializationFailed(true); setInitState("initialization_error");
      const message = cause instanceof ApiError && typeof cause.detail === "object" && cause.detail ? String((cause.detail as { message?: string }).message || cause.message) : cause instanceof DOMException && cause.name === "AbortError" ? "Initialization timed out while waiting for the backend." : cause instanceof Error ? cause.message : "Candidate initialization failed";
      showError(message, "INITIALIZATION ERROR");
    } finally { setBusy(false); }
  }

  async function createProject() {
    if (projectId) return;
    setBusy(true); setError("");
    try {
      const data = await request("/projects", { method: "POST", body: JSON.stringify({ name: project || "Rank & Rent Project", profile }) });
      setProjectId(data.id); sessionStorage.setItem("nicheforge_current_project_id", data.id);
    } catch (cause) { setInitializationFailed(true); setInitState("initialization_error"); showError(cause instanceof Error ? cause.message : "Project creation failed", "INITIALIZATION ERROR"); }
    finally { setBusy(false); }
  }

  async function chooseLocation(candidate: LocationCandidate) {
    if (!projectId || !handoffs.length) return;
    setBusy(true); setError(""); setLocationCandidates([]); setInitState("attaching_candidate");
    try {
      const handoffId = locationAmbiguities.find(item => item.candidates.some(option => option.city_id === candidate.city_id))?.handoff_id || handoffs[0]?.handoff_id;
      const nextLocations = { ...selectedLocations, [handoffId]: candidate };
      setSelectedLocations(nextLocations);
      const data = await request(`/projects/${encodeURIComponent(projectId)}/handoffs/attach`, { method: "POST", body: JSON.stringify({ handoff_ids: handoffs.map(item => item.handoff_id), location_overrides: Object.fromEntries(Object.entries(nextLocations).map(([id, value]) => [id, { city: value.city, state_code: value.state, city_id: value.city_id }])) }) });
      const count = Number(data.created_count || 0) + Number(data.existing_count || 0);
      setCandidateCount(count); setAttached(count > 0); setLocationAmbiguities([]); setInitState("previewing");
      setAttachOutcomes(items => items.map(item => item.handoff_id === handoffId ? { ...item, status: "LOCAL_READY", project_candidate_id: data.project_candidate_ids?.[0] } : item));
      setPreview(await request(`/projects/${encodeURIComponent(projectId)}/validation-preview`, { method: "POST", body: JSON.stringify({ profile, candidate_ids: data.project_candidate_ids }) }));
      setInitState("ready");
    } catch (cause) {
      if (cause instanceof ApiError && typeof cause.detail === "object" && cause.detail && ["HANDOFF_CITY_AMBIGUOUS", "HANDOFF_CITY_UNRESOLVED"].includes((cause.detail as { code?: string }).code || "") && (((cause.detail as { candidates?: LocationCandidate[] }).candidates || []).length > 0 || ((cause.detail as { ambiguities?: unknown[] }).ambiguities || []).length > 0)) {
        const detail = cause.detail as { handoff_id?: string; keyword?: string; candidates?: LocationCandidate[]; ambiguities?: Array<{ handoff_id: string; keyword: string; candidates: LocationCandidate[] }> };
        const ambiguities = detail.ambiguities || [{ handoff_id: detail.handoff_id || handoffs[0]?.handoff_id || "", keyword: detail.keyword || handoffs[0]?.keyword || "", candidates: detail.candidates || [] }];
        setLocationAmbiguities(ambiguities); setError(""); setErrorKind("LOCATION CONFIRMATION REQUIRED"); setInitState("location_confirmation_required");
      } else { setInitState("initialization_error"); showError(cause instanceof Error ? cause.message : "Candidate initialization failed", "INITIALIZATION ERROR"); }
    }
    finally { setBusy(false); }
  }

  async function attachHandoffs(targetProjectId = projectId) {
    if (!targetProjectId || !handoffs.length || attached) return;
    setBusy(true); setError("");
    try {
      const data = await request(`/projects/${targetProjectId}/handoffs/attach`, { method: "POST", body: JSON.stringify({ handoff_ids: handoffs.map(item => item.handoff_id) }) });
      setCandidateCount(Number(data.created_count || 0) + Number(data.existing_count || 0)); setAttached(true); await previewRun(targetProjectId);
    } catch (cause) { setInitializationFailed(true); showError(cause instanceof Error ? cause.message : "Handoff attachment failed", "INITIALIZATION ERROR"); }
    finally { setBusy(false); }
  }

  async function previewRun(targetProjectId = projectId) {
    if (!targetProjectId || !attached && !handoffs.length) return;
    try { setPreview(await request(`/projects/${targetProjectId}/validation-preview`, { method: "POST", body: JSON.stringify({ profile }) })); }
    catch (cause) { showError(cause instanceof Error ? cause.message : "Preview failed", "API ERROR"); }
  }

  async function startRun() {
    if (!projectId || !attached || candidateCount < 1) { showError("Attach at least one Search Volume handoff before starting.", "VALIDATION REJECTED"); return; }
    setBusy(true); setError("");
    try { const created = await request(`/projects/${projectId}/runs`, { method: "POST", body: JSON.stringify({ profile, candidate_ids: [] }) }) as Run; setRun(created); setRun(await request(`/runs/${created.id}/execute`, { method: "POST", body: JSON.stringify({ profile }) }) as Run); }
    catch (cause) { showError(cause instanceof Error ? cause.message : "Validation run failed", "RUN FAILED"); }
    finally { setBusy(false); }
  }

  return <AppShell active="Niche Validator">
    <header className="page-head"><div><p className="eyebrow">Rank &amp; Rent</p><h1>Rank &amp; Rent Validation Run</h1><p className="muted">Validate promising local keywords through Population -&gt; Search Volume -&gt; SERP -&gt; DA -&gt; Deeper Analysis -&gt; KD -&gt; Result.</p></div></header>
    {selected && <section className="card handoff-arrival"><div><strong>Imported from Search Volume</strong><h2>{selected.keyword}</h2><div className="handoff-meta"><span>SV {selected.search_volume ?? "Unavailable"}</span><span>{selected.provider}</span><span>Evidence reused</span><span>Status {selected.status}</span></div></div><span className="badge success">HANDOFF READY</span></section>}
    {handoffs.length > 1 && <section className="card selector-card"><label htmlFor="handoff-select">Search Volume handoff</label><select id="handoff-select" value={selected?.handoff_id || ""} onChange={event => setSelected(handoffs.find(item => item.handoff_id === event.target.value) || null)}>{handoffs.map(item => <option value={item.handoff_id} key={item.handoff_id}>{item.keyword} - SV {item.search_volume ?? "-"}</option>)}</select></section>}
    <section className="card lifecycle"><div className="stage-strip">{stages.map((stage, index) => <div className={`stage ${run ? (index === 0 ? "complete" : index === 1 ? "active" : "conditional") : index === 0 ? "active" : ""}`} key={stage}><span className="stage-circle">{index + 1}</span><span className="stage-name">{stage}</span><span className="stage-state">{run ? (index === 0 ? "Complete" : index === 1 ? "Current" : "Conditional") : index === 0 ? "Ready" : "Waiting"}</span></div>)}</div></section>
    <section className="run-grid"><section className="card card-body"><h2>Imported Rank &amp; Rent Candidate</h2><p className="muted">The handed-off Search Volume evidence is reused for validation.</p>{selected && <div className="handoff-meta"><strong>{selected.keyword}</strong><span>SV {selected.search_volume ?? "Unavailable"}</span><span>Evidence reused</span></div>}<label htmlFor="project-name">Project name<input id="project-name" value={project} onChange={event => setProject(event.target.value)} placeholder="Rank & Rent Project" /></label><div className="form-actions"><button className="button secondary" type="button" onClick={createProject} disabled={busy || !!projectId}>{projectId ? "Project ready" : "Create project"}</button><span className="muted">{projectId ? `Project ${projectId}` : initState === "initialization_error" ? "Project setup failed" : initState === "ready" ? "Project ready" : initState === "attaching_candidate" ? "Attaching candidate" : initState === "previewing" ? "Preparing preview" : "Setting up project"}</span></div><p className="muted">{initState === "ready" ? `${candidateCount} executable candidate(s) attached.` : initState === "initialization_error" ? "Candidate setup needs attention." : initState === "previewing" ? "Refreshing validation preview..." : "Setting up candidate..."}</p></section><section className="card card-body"><h2>Validation Profile</h2><div className="settings-grid"><Setting label="Population" value="20k - 120k" /><Setting label="Minimum SV" value="260" /><Setting label="DA gate" value="&lt; 10 / 4 required" /><Setting label="KD" value="Priority / 15" /></div></section></section>
    {attachOutcomes.length > 0 && <section className="card card-body mixed-summary"><h2>Mixed validation candidates</h2><div className="preview-grid"><Stat label="Candidates" value={attachOutcomes.length} /><Stat label="Ready" value={attachOutcomes.filter(item => item.status.endsWith("READY")).length} /><Stat label="Needs location" value={attachOutcomes.filter(item => item.status === "LOCAL_LOCATION_REQUIRED").length} /><Stat label="Local / General" value={`${attachOutcomes.filter(item => item.validation_scope === "LOCAL_RANK_RENT").length} / ${attachOutcomes.filter(item => item.validation_scope === "GENERAL_NICHE").length}`} /></div></section>}
    {attachOutcomes.length > 0 && <section className="mixed-candidate-grid">{attachOutcomes.map(item => { const handoff = handoffs.find(row => row.handoff_id === item.handoff_id); const general = item.validation_scope === "GENERAL_NICHE"; const pending = item.status === "LOCAL_LOCATION_REQUIRED"; return <article className="card card-body candidate-scope-card" key={item.handoff_id}><div className="progress-head"><h2>{item.keyword || handoff?.keyword || "Candidate"}</h2><span className="badge">{general ? "GENERAL NICHE" : "LOCAL RANK & RENT"}</span></div><p><strong>Status:</strong> {pending ? "LOCATION CONFIRMATION REQUIRED" : item.status === "GENERAL_READY" ? "READY" : item.status}</p>{general ? <><p><strong>Target:</strong> {handoff?.country_code || "US"}</p><p><strong>Location:</strong> Not required</p><p><strong>Population:</strong> NOT APPLICABLE</p><p><strong>SERP Mode:</strong> NATIONAL</p>{item.authority_opportunity && <div className="evidence-detail"><strong>Authority Opportunity: {item.authority_opportunity}</strong><span>Weak sites: {item.weak_site_count ?? "Unavailable"} / analyzed</span><span>Threshold: DA &lt; {item.authority_threshold ?? 20}</span>{item.authority_opportunity_reason && <small>{item.authority_opportunity_reason}</small>}</div>}<p className="muted">Pipeline: SV â†’ National SERP â†’ Authority Opportunity â†’ Deep Analysis â†’ KD â†’ Result</p></> : <><p><strong>Population:</strong> {pending ? "Pending location" : "Applicable"}</p><p><strong>SERP Mode:</strong> Localized</p><p className="muted">Pipeline: Population â†’ SV â†’ Local SERP â†’ Authority â†’ Deep Analysis â†’ KD â†’ Result</p></>}</article>; })}</section>}
    {error && <div className="error-banner"><strong>{errorKind}</strong><span>{error}</span></div>}
    {locationAmbiguities.length > 0 && <section className="card card-body"><h2>Location confirmation required</h2><p className="muted">Choose a city for each keyword before validation continues.</p>{locationAmbiguities.map(item => <div className="location-choice" key={item.handoff_id}><strong>{item.keyword}</strong><span className="muted">Needs confirmation</span><div className="form-actions">{item.candidates.map(candidate => <button className="button secondary" type="button" key={candidate.city_id} onClick={() => chooseLocation(candidate)} disabled={busy}>{candidate.city}, {candidate.state}</button>)}</div></div>)}</section>}
    {locationCandidates.length > 0 && !locationAmbiguities.length && <section className="card card-body"><h2>Location confirmation required</h2><p className="muted">Select the intended city before Rank &amp; Rent validation continues.</p><div className="form-actions">{locationCandidates.map(candidate => <button className="button secondary" type="button" key={candidate.city_id} onClick={() => chooseLocation(candidate)} disabled={busy}>{candidate.city}, {candidate.state}</button>)}</div></section>}
    <section className="card card-body preview-card"><div className="section-heading"><h2>Validation Preview</h2><p className="muted">Preview is zero-network. Downstream SERP, DA, Deep Analysis, and KD work is conditional on earlier gates.</p></div><div className="preview-footer"><span className="badge success">NO PROVIDER CALLS</span><button className="button secondary" type="button" onClick={() => previewRun()} disabled={!projectId || busy}>{busy ? "Preparing preview..." : "Refresh Preview"}</button></div>{preview && <div className="preview-grid"><Stat label="Candidates" value={preview.candidate_count} /><Stat label="Reusable SV" value={preview.reusable_search_volume ? `${preview.reusable_search_volume} Â· Reused` : "-"} /><Stat label="Estimated work" value={preview.estimated_provider_calls} /><Stat label="DA / KD" value="Conditional" /></div>}</section>
    {run && <section className="card card-body run-workspace"><div className="progress-head"><strong>Validation Run {run.id}</strong><span>{run.status}</span></div><div className="progress"><div className="progress-bar" style={{ width: `${progress}%` }} /></div><div className="run-meta"><span>Run progress {progress}%</span><span>Provider work is controlled by the backend</span><span>Evidence is persisted per stage</span></div>{run.candidate_results?.map((result, index) => <details className="run-result" key={index} open={run.candidate_results?.length === 1}><summary><strong>{result.keyword || "Candidate"}</strong> Â· {result.status === "ERROR_RETRYABLE" ? "RETRYABLE" : result.final_result}</summary><div className="stage-table">{[["Population", result.population, "City fits your configured population range."], ["Search Volume", result.search_volume_value != null ? `${result.search_volume_value} Â· Reused` : result.search_volume, "Stored evidence was reused; Google Ads was not called again."], ["SERP", result.serp, result.serp_reason === "SERP_PROVIDER_REQUEST_ERROR" ? "The SERP provider rejected the request; this is not a niche rejection." : result.serp === "RETRYABLE" ? `${result.serp_count || 0} usable organic results found; ${result.serp_required || 0} required.` : "Localized organic results were collected."], ["DA Gate", result.da, result.da === "NOT RUN" ? "Waiting for a valid SERP before checking domain authority." : "Authority gate evaluated ranking domains."], ["Deep Analysis", result.deep_analysis, result.deep_analysis === "NOT RUN" ? "Runs only after the primary SERP and DA gates qualify." : `${result.da_evidence?.length || 0} authority records captured.`], ["KD", result.kd, result.kd === "NOT RUN" ? "KD is checked only after the primary DA gate passes." : "Keyword difficulty was evaluated."], ["Final Result", result.final_result, result.final_result === "NOT PRODUCED" ? "No final PASS/FAIL decision was made." : "Final validation result."]].map(([stage, status, note]) => <div className="stage-row" key={stage}><strong>{stage}</strong><span>{status}</span><small>{note}</small></div>)}</div>{result.serp_evidence?.length ? <div className="evidence-detail"><strong>SERP evidence: {result.serp_evidence.length} result(s)</strong>{result.serp_evidence.map(item => <span key={item.position}>#{item.position} {item.domain}</span>)}</div> : null}{result.da_evidence?.length ? <div className="evidence-detail"><strong>Authority evidence</strong>{result.da_evidence.map(item => <span key={item.position}>#{item.position} {item.domain} Â· DA {item.da ?? "Not available"}{item.pa != null ? ` Â· PA ${item.pa}` : ""}</span>)}</div> : null}{result.reason_codes.length > 0 && <small>Technical details: {result.reason_codes.join(", ")}</small>}</details>)}</section>}
    <section className="card card-body start-panel"><div><h2>Start Validation</h2><p className="muted">The backend-confirmed candidate is ready. Starting validation may invoke configured downstream providers.</p><p className="muted">{candidateCount} executable candidate{candidateCount === 1 ? "" : "s"} ready.</p></div><button className="button primary" type="button" onClick={startRun} disabled={initState !== "ready" || !projectId || !attached || candidateCount < 1 || !preview || busy}>{busy ? "Validation running..." : "Start Validation"}</button></section>
  </AppShell>;
}

function Setting({ label, value }: { label: string; value: string }) { return <div className="setting"><span>{label}</span><strong dangerouslySetInnerHTML={{ __html: value }} /></div>; }
function Stat({ label, value }: { label: string; value: unknown }) { return <div className="metric"><span>{label}</span><strong>{String(value ?? "-")}</strong></div>; }


```

# FILE: frontend/app/rank-rent/validator/validator.css

```css
Exit code: 0
Wall time: 1.8 seconds
Output:
.page-head{display:flex;justify-content:space-between;gap:1.25rem;align-items:flex-start;margin-bottom:1.25rem}.header-actions,.form-actions{display:flex;gap:.75rem;align-items:center;flex-wrap:wrap}.card{background:#fff;border:1px solid #e2e8f0;border-radius:14px;box-shadow:0 8px 28px rgba(15,23,42,.05);margin-bottom:1rem}.card-body{padding:1.25rem}.card h2{margin:.1rem 0 .45rem;font-size:1.1rem}.muted{color:#64748b}.handoff-arrival{display:flex;justify-content:space-between;align-items:center;gap:1rem;padding:1.1rem 1.25rem;background:#eff6ff;border-color:#bfdbfe}.handoff-arrival strong{color:#1e40af}.handoff-arrival h2{margin:.3rem 0;font-size:1.1rem}.handoff-meta{display:flex;gap:.9rem;flex-wrap:wrap;color:#334155;font-size:.82rem}.badge{border-radius:999px;padding:.4rem .7rem;font-size:.72rem;font-weight:800;white-space:nowrap}.badge.success{background:#dcfce7;color:#15803d}.selector-card{display:flex;gap:1rem;align-items:center;padding:1rem 1.25rem}.selector-card select,.card input{border:1px solid #cbd5e1;border-radius:8px;padding:.65rem .75rem;background:#fff}.selector-card select{min-width:240px}.lifecycle{overflow:hidden}.stage-strip{display:grid;grid-template-columns:repeat(7,minmax(100px,1fr));padding:1.25rem;overflow-x:auto}.stage{text-align:center;position:relative;min-width:100px}.stage:not(:last-child)::after{content:"â†’";position:absolute;right:-.35rem;top:.65rem;color:#94a3b8}.stage-circle{display:flex;width:34px;height:34px;margin:0 auto .45rem;align-items:center;justify-content:center;border-radius:50%;border:2px solid #cbd5e1;color:#64748b;font-weight:800}.stage.complete .stage-circle{background:#dcfce7;border-color:#22c55e;color:#15803d}.stage.active .stage-circle{background:#dbeafe;border-color:#2563eb;color:#1d4ed8}.stage.conditional .stage-circle{background:#fffbeb;border-color:#f59e0b;color:#b45309}.stage-name{display:block;font-size:.76rem;font-weight:750}.stage-state{display:block;color:#64748b;font-size:.68rem;margin-top:.2rem}.run-grid{display:grid;grid-template-columns:1fr 1fr;gap:1rem}.card label{display:flex;flex-direction:column;gap:.4rem;color:#475569;font-weight:700;font-size:.82rem}.card label input{margin-top:.25rem}.settings-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:.7rem}.setting,.metric{display:flex;flex-direction:column;gap:.25rem;padding:.75rem;border:1px solid #e2e8f0;border-radius:9px;background:#f8fafc}.setting span,.metric span{color:#64748b;font-size:.72rem}.setting strong,.metric strong{color:#172554}.button{border:1px solid #cbd5e1;border-radius:8px;padding:.65rem .9rem;font-weight:750;background:#fff;color:#172554}.button.primary{background:#3159d8;color:#fff;border-color:#3159d8}.button:disabled{opacity:.55;cursor:not-allowed}.section-heading h2{margin:0}.preview-footer,.run-meta,.progress-head{display:flex;justify-content:space-between;gap:1rem;align-items:center;flex-wrap:wrap}.preview-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:.75rem;margin-top:1rem}.error-banner{margin-bottom:1rem;padding:.85rem 1rem;border:1px solid #fecaca;background:#fef2f2;color:#991b1b;border-radius:9px}.run-workspace .progress{height:10px;background:#e2e8f0;border-radius:999px;overflow:hidden;margin:1rem 0}.progress-bar{height:100%;background:#3159d8;border-radius:inherit;transition:width .15s ease-out}.run-meta{font-size:.75rem;color:#64748b}.start-panel{display:flex;justify-content:space-between;align-items:center;gap:1rem}@media(max-width:900px){.run-grid{grid-template-columns:1fr}.preview-grid{grid-template-columns:repeat(2,1fr)}.stage-strip{grid-template-columns:repeat(4,minmax(100px,1fr));row-gap:1rem}.stage:not(:last-child)::after{display:none}}@media(max-width:620px){.page-head,.handoff-arrival,.start-panel,.selector-card{flex-direction:column;align-items:stretch}.preview-grid,.settings-grid{grid-template-columns:1fr}.stage-strip{grid-template-columns:repeat(2,1fr);overflow:visible}.stage{min-width:0}.header-actions{width:100%}.header-actions .button{flex:1}}
.mixed-candidate-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; margin: 20px 0; }
.candidate-scope-card { min-width: 0; }
.candidate-scope-card h2 { margin: 0; font-size: 1.05rem; }
.candidate-scope-card .progress-head { align-items: flex-start; gap: 12px; }
.candidate-scope-card .badge { white-space: nowrap; }
@media (max-width: 900px) { .mixed-candidate-grid { grid-template-columns: 1fr 1fr; } }
@media (max-width: 600px) { .mixed-candidate-grid { grid-template-columns: 1fr; } }


```

