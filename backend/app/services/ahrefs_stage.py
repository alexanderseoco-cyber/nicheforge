"""Internal Ahrefs DR enrichment boundary."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Run, RunCandidate, RunCandidateProxyAuthorityEvidence, SerpResultRow
from app.services.normalization import root_domain
from app.services.proxy_authority import evaluate_run_candidate_proxy


@dataclass(frozen=True)
class AhrefsStageResult:
    dr_by_domain: dict[str, float | None]
    evidence_ids: tuple[str, ...]
    coverage_count: int
    requested_count: int
    weak_dr_count: int
    provider: str | None
    executed: bool
    available: bool


async def execute_ahrefs_stage(
    db: Session,
    run: Run,
    run_candidate: RunCandidate,
    rows: list[SerpResultRow],
    *,
    threshold: float = 14.0,
    minimum_weak: int = 4,
    ideal_weak: int = 5,
) -> AhrefsStageResult:
    """Run the existing Ahrefs implementation and normalize its persisted facts."""
    await evaluate_run_candidate_proxy(db, run, run_candidate, rows, threshold, minimum_weak, ideal_weak)
    links = db.scalars(
        select(RunCandidateProxyAuthorityEvidence).where(
            RunCandidateProxyAuthorityEvidence.run_candidate_id == run_candidate.id
        )
    ).all()
    by_row = {row.id: row for row in rows}
    dr_by_domain: dict[str, float | None] = {}
    evidence_ids: list[str] = []
    for link in links:
        row = by_row.get(link.serp_result_row_id)
        if row is None:
            continue
        domain = root_domain(row.url) or row.root_domain
        dr_by_domain[domain] = link.dr_value_used
        if link.proxy_authority_evidence_id not in evidence_ids:
            evidence_ids.append(link.proxy_authority_evidence_id)
    observed = [value for value in dr_by_domain.values() if value is not None]
    return AhrefsStageResult(
        dr_by_domain=dr_by_domain,
        evidence_ids=tuple(evidence_ids),
        coverage_count=len(observed),
        requested_count=len({root_domain(row.url) or row.root_domain for row in rows}),
        weak_dr_count=sum(value <= threshold for value in observed),
        provider="ahrefs" if links else None,
        executed=True,
        available=bool(observed),
    )


def ahrefs_stage_not_executed(rows: list[SerpResultRow]) -> AhrefsStageResult:
    return AhrefsStageResult({}, (), 0, len({root_domain(row.url) or row.root_domain for row in rows}), 0, None, False, False)
