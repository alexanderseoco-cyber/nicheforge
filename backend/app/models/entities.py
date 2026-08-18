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


class ProviderLocationIdentity(Base):
    __tablename__ = "provider_location_identities"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    city_id: Mapped[str] = mapped_column(ForeignKey("cities.id"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    location_code: Mapped[int] = mapped_column(Integer, nullable=False)
    provider_location_name: Mapped[str] = mapped_column(String(240), nullable=False)
    country_code: Mapped[str] = mapped_column(String(8), nullable=False)
    state_code: Mapped[str] = mapped_column(String(16), nullable=False)
    city_name: Mapped[str] = mapped_column(String(120), nullable=False)
    location_type: Mapped[str] = mapped_column(String(40), nullable=False, default="City")
    source: Mapped[str] = mapped_column(String(40), nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    imported_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    __table_args__ = (
        UniqueConstraint("provider", "city_id", name="uq_provider_location_city"),
        UniqueConstraint("provider", "country_code", "location_code", name="uq_provider_location_code"),
    )


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
    minimum_organic_rows: Mapped[int | None] = mapped_column(Integer, nullable=True)
    minimum_organic_coverage: Mapped[float | None] = mapped_column(Float, nullable=True)
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
    parent_run_candidate_id: Mapped[str | None] = mapped_column(ForeignKey("run_candidates.id"), nullable=True, index=True)
    validation_scope: Mapped[str] = mapped_column(String(30), default="LOCAL_RANK_RENT", index=True)
    authority_opportunity_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default=CandidateStatus.IMPORTED)
    automatic_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    reason_codes: Mapped[list] = mapped_column(JSON, default=list)
    population_evidence_id: Mapped[str | None] = mapped_column(ForeignKey("population_evidence.id"), nullable=True)
    search_volume_evidence_id: Mapped[str | None] = mapped_column(ForeignKey("search_volume_evidence.id"), nullable=True)
    # Canonical handoff lineage; the legacy column remains for historical rows.
    keyword_metric_evidence_id: Mapped[str | None] = mapped_column(ForeignKey("keyword_metric_evidence.id"), nullable=True, index=True)
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


class RunCandidateProxyAuthorityEvidence(Base):
    __tablename__ = "run_candidate_proxy_authority_evidence"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    run_candidate_id: Mapped[str] = mapped_column(ForeignKey("run_candidates.id"), index=True)
    serp_result_row_id: Mapped[str] = mapped_column(ForeignKey("serp_results.id"), index=True)
    proxy_authority_evidence_id: Mapped[str] = mapped_column(ForeignKey("proxy_authority_evidence.id"), index=True)
    ranking_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dr_value_used: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("run_candidate_id", "serp_result_row_id", name="uq_run_candidate_serp_proxy_authority"),)


class RunCandidateBacklinkEvidence(Base):
    __tablename__ = "run_candidate_backlink_evidence"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    run_candidate_id: Mapped[str] = mapped_column(ForeignKey("run_candidates.id"), index=True)
    serp_result_row_id: Mapped[str] = mapped_column(ForeignKey("serp_results.id"), index=True)
    proxy_backlink_evidence_id: Mapped[str] = mapped_column(ForeignKey("proxy_backlink_feature_evidence.id"), index=True)
    ranking_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("run_candidate_id", "serp_result_row_id", name="uq_run_candidate_serp_backlink"),)


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
    provider_name: Mapped[str | None] = mapped_column(String(240), nullable=True)
    canonical_name: Mapped[str | None] = mapped_column(String(400), nullable=True)
    target_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    provider_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    mapping_status: Mapped[str] = mapped_column(String(40), default="MAPPED")
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    fresh_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    provenance: Mapped[dict] = mapped_column(JSON, default=dict)
    __table_args__ = (UniqueConstraint("city", "state_code", "country_code", "provider", name="uq_provider_geo_identity"),)


class ProviderCountryGeoMapping(Base):
    """Validated provider-owned country target identity."""
    __tablename__ = "provider_country_geo_mappings"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    country_code: Mapped[str] = mapped_column(String(2), index=True)
    provider: Mapped[str] = mapped_column(String(80), index=True)
    criterion_id: Mapped[str] = mapped_column(String(80))
    resource_name: Mapped[str] = mapped_column(String(200))
    provider_name: Mapped[str | None] = mapped_column(String(240), nullable=True)
    target_type: Mapped[str] = mapped_column(String(40))
    provider_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    mapping_status: Mapped[str] = mapped_column(String(40), default="MAPPED")
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    provenance: Mapped[dict] = mapped_column(JSON, default=dict)
    __table_args__ = (UniqueConstraint("country_code", "provider", name="uq_provider_country_geo_identity"),)


class ProviderCustomerMetadata(Base):
    __tablename__ = "provider_customer_metadata"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    provider: Mapped[str] = mapped_column(String(80), index=True)
    customer_id: Mapped[str] = mapped_column(String(40), index=True)
    currency_code: Mapped[str | None] = mapped_column(String(3), nullable=True)
    time_zone: Mapped[str | None] = mapped_column(String(80), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    fresh_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    provenance: Mapped[dict] = mapped_column(JSON, default=dict)
    __table_args__ = (UniqueConstraint("provider", "customer_id", name="uq_provider_customer_metadata"),)


class FxRateEvidence(Base):
    __tablename__ = "fx_rate_evidence"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    source_currency: Mapped[str] = mapped_column(String(3), index=True)
    target_currency: Mapped[str] = mapped_column(String(3), index=True)
    mode: Mapped[str] = mapped_column(String(16), default="latest")
    requested_as_of_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    provider_effective_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    rate: Mapped[float] = mapped_column(Numeric(24, 12))
    provider: Mapped[str] = mapped_column(String(100))
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    fresh_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    provenance: Mapped[dict] = mapped_column(JSON, default=dict)
    __table_args__ = (UniqueConstraint("source_currency", "target_currency", "mode", "requested_as_of_date", "provider", name="uq_fx_rate_identity"),)


class KeywordOpportunityMetrics(Base):
    __tablename__ = "keyword_opportunity_metrics"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    keyword_metric_evidence_id: Mapped[str] = mapped_column(ForeignKey("keyword_metric_evidence.id"), index=True)
    commercial_search_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    projected_metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    ctr_model_version: Mapped[str] = mapped_column(String(40))
    calculation_version: Mapped[str] = mapped_column(String(80))
    calculated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("keyword_metric_evidence_id", "ctr_model_version", "calculation_version", name="uq_keyword_opportunity_calculation"),)


class KeywordMetricBatchItem(Base):
    """Stable per-keyword/location state used for resumable batch execution."""
    __tablename__ = "keyword_metric_batch_items"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    batch_id: Mapped[str] = mapped_column(ForeignKey("keyword_metric_batches.id"), index=True)
    keyword: Mapped[str] = mapped_column(String(400), index=True)
    city: Mapped[str] = mapped_column(String(120), index=True)
    state_code: Mapped[str] = mapped_column(String(8), index=True)
    country_code: Mapped[str] = mapped_column(String(2), default="US")
    location_identity: Mapped[str] = mapped_column(String(300), index=True)
    status: Mapped[str] = mapped_column(String(40), default="PENDING")
    geo_mapping_id: Mapped[str | None] = mapped_column(ForeignKey("provider_geo_mappings.id"), nullable=True)
    evidence_id: Mapped[str | None] = mapped_column(ForeignKey("keyword_metric_evidence.id"), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    geo_diagnostic: Mapped[dict] = mapped_column(JSON, default=dict)
    policy_status: Mapped[str | None] = mapped_column(String(60), nullable=True)
    policy_minimum_sv: Mapped[int | None] = mapped_column(Integer, nullable=True)
    policy_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    __table_args__ = (UniqueConstraint("batch_id", "keyword", "location_identity", name="uq_keyword_metric_batch_item"),)


class KeywordMetricValidationHandoff(Base):
    """Explicit subset handoff; points to immutable evidence, never copies it."""
    __tablename__ = "keyword_metric_validation_handoffs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    evidence_id: Mapped[str] = mapped_column(ForeignKey("keyword_metric_evidence.id"), index=True)
    submitted_keyword: Mapped[str] = mapped_column(String(400))
    provider: Mapped[str] = mapped_column(String(80))
    provider_keyword: Mapped[str | None] = mapped_column(String(400), nullable=True)
    location_target: Mapped[dict] = mapped_column(JSON, default=dict)
    language_code: Mapped[str] = mapped_column(String(16), default="en")
    country_code: Mapped[str] = mapped_column(String(2), default="US")
    validation_profile_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(30), default="QUEUED")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


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
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
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
    # Nullable observational cost/cache telemetry. These fields are intentionally
    # not used by validation decisions; existing ProviderCall fields above remain
    # authoritative for their original meanings.
    logical_item_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    unique_target_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cache_hit_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cache_miss_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stale_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cache_outcome: Mapped[str | None] = mapped_column(String(40), nullable=True)
    cache_provider_dimension: Mapped[str | None] = mapped_column(String(80), nullable=True)
    actual_evidence_provider: Mapped[str | None] = mapped_column(String(80), nullable=True)
    evidence_reused_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evidence_created_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evidence_partial_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evidence_missing_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    provider_item_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    items_returned_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    items_failed_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    batch_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    batch_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    batch_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    http_request_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retry_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    http_request_sent: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    paid_attempt: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    reuse_scope: Mapped[str | None] = mapped_column(String(30), nullable=True)
    cost_confidence: Mapped[str | None] = mapped_column(String(20), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
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
