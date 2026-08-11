from __future__ import annotations
from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, JSON, Boolean, UniqueConstraint, Index
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
    city_id: Mapped[str] = mapped_column(ForeignKey("cities.id"), index=True)
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


class KeywordDifficultyEvidence(Base):
    __tablename__ = "keyword_difficulty_evidence"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    candidate_entity_id: Mapped[str] = mapped_column(ForeignKey("candidate_entities.id"), index=True)
    keyword: Mapped[str] = mapped_column(String(400), index=True)
    location_name: Mapped[str | None] = mapped_column(String(240), nullable=True)
    language_code: Mapped[str] = mapped_column(String(16), default="en")
    country_code: Mapped[str] = mapped_column(String(2), default="US")
    provider: Mapped[str] = mapped_column(String(80), index=True)
    metric_type: Mapped[str] = mapped_column(String(40), default="keyword_difficulty")
    difficulty: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_kind: Mapped[str] = mapped_column(String(40), default="mock")
    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    request_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    fresh_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Candidate(Base):
    __tablename__ = "candidates"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    city_id: Mapped[str | None] = mapped_column(ForeignKey("cities.id"), nullable=True, index=True)
    broad_category: Mapped[str | None] = mapped_column(String(160), nullable=True)
    micro_niche: Mapped[str | None] = mapped_column(String(160), nullable=True)
    service_term: Mapped[str] = mapped_column(String(240), index=True)
    normalized_keyword: Mapped[str] = mapped_column(String(400), index=True)
    display_keyword: Mapped[str] = mapped_column(String(400))
    status: Mapped[str] = mapped_column(String(40), default=CandidateStatus.IMPORTED)
    search_volume: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cpc: Mapped[float | None] = mapped_column(Float, nullable=True)
    low_da_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    secondary_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    automatic_pass: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    reason_codes: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
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
    run_id: Mapped[str | None] = mapped_column(ForeignKey("runs.id"), nullable=True, index=True)
    run_candidate_id: Mapped[str | None] = mapped_column(ForeignKey("run_candidates.id"), nullable=True, index=True)


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
