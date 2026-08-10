from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.entities import Candidate, CandidateStatus, SerpSnapshot, SerpResultRow, AuthorityMetric
from app.schemas.domain import ValidationProfile
from app.providers.factory import search_volume_provider, serp_provider, authority_provider
from app.providers.contracts import KeywordMetricRequest, SerpRequest, AuthorityTarget
from app.services.normalization import root_domain
from app.services.gates import search_volume_gate, authority_gate


async def process_candidate(db: Session, candidate: Candidate, profile: ValidationProfile) -> Candidate:
    if candidate.city is None:
        candidate.status = CandidateStatus.ERROR_TERMINAL
        candidate.reason_codes = ["CITY_REQUIRED"]
        db.commit()
        return candidate

    # Stage 1: SV
    svp = search_volume_provider()
    location_name = f"{candidate.city.name}, {candidate.city.state_code}, United States"
    sv = (await svp.fetch([KeywordMetricRequest(candidate.normalized_keyword, location_name)]))[0]
    candidate.search_volume = sv.avg_monthly_searches
    candidate.cpc = sv.cpc
    sv_decision = search_volume_gate(candidate.search_volume, profile)
    if not sv_decision.passed:
        candidate.status = CandidateStatus.SV_REJECTED
        candidate.automatic_pass = False
        candidate.reason_codes = sv_decision.reason_codes
        db.commit(); db.refresh(candidate)
        return candidate

    # Stage 2: SERP
    candidate.status = CandidateStatus.SERP_PENDING
    db.flush()
    sp = serp_provider()
    serp = (await sp.fetch([SerpRequest(candidate.normalized_keyword, location_name, depth=profile.organic_depth)]))[0]
    snap = SerpSnapshot(candidate_id=candidate.id, provider=serp.provider, raw_payload=serp.raw or {})
    db.add(snap); db.flush()
    targets = []
    for item in serp.organic[:profile.organic_depth]:
        rd = root_domain(item.url)
        db.add(SerpResultRow(snapshot_id=snap.id, position=item.position, title=item.title, url=item.url, root_domain=rd))
        targets.append(AuthorityTarget(item.url, rd))
    candidate.status = CandidateStatus.AUTHORITY_PENDING
    db.flush()

    # Stage 3: authority
    ap = authority_provider()
    metrics = await ap.fetch(targets)
    for m in metrics:
        db.add(AuthorityMetric(
            target_key=m.url, target_type="URL", provider=m.provider, da=m.da, pa=m.pa,
            spam_score=m.spam_score, linking_root_domains=m.linking_root_domains,
            backlinks=m.backlinks, raw_payload=m.raw or {},
        ))
    decision, low_count = authority_gate([m.da for m in metrics], profile)
    candidate.low_da_count = low_count
    candidate.reason_codes = decision.reason_codes
    candidate.automatic_pass = decision.passed
    candidate.status = CandidateStatus.SECONDARY_PENDING if decision.passed else CandidateStatus.PRIMARY_REJECTED
    db.commit(); db.refresh(candidate)
    return candidate
