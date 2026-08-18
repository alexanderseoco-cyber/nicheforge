from __future__ import annotations

from app.providers.contracts import AuthorityTarget, BacklinkFeatureResult
from app.providers.dataforseo import DataForSEOClient
from app.services.normalization import root_domain


class DataForSEOBacklinkSummaryProvider:
    """Separate DataForSEO backlink feature source for proxy enrichment."""

    provider = "dataforseo"
    operation = "backlinks_bulk_pages_summary_live"
    endpoint = "/v3/backlinks/bulk_pages_summary/live"

    def __init__(self, login: str, password: str, enabled: bool = False,
                 live_approved: bool = False, estimated_cost: float = 0.0,
                 batch_size: int = 1000, budget: float = 0.0):
        self.client = DataForSEOClient(login, password)
        self.enabled = enabled
        self.live_approved = live_approved
        self.estimated_cost = estimated_cost
        self.batch_size = min(max(1, batch_size), 1000)
        self.budget = budget
        self.last_batch_reports: list[dict] = []

    def validate_live_execution(self) -> None:
        if not self.enabled:
            raise RuntimeError("DATAFORSEO_BACKLINK_PROXY_ENABLED must be true before backlink enrichment")
        if not self.live_approved:
            raise RuntimeError("DATAFORSEO_BACKLINK_LIVE_APPROVED must be true before backlink enrichment")
        if self.estimated_cost > self.budget:
            raise RuntimeError("Estimated DataForSEO backlink cost exceeds configured backlink budget")

    async def fetch(self, targets: list[AuthorityTarget]) -> list[BacklinkFeatureResult]:
        self.validate_live_execution()
        if not targets:
            return []
        output: list[BacklinkFeatureResult] = []
        self.last_batch_reports = []
        for start in range(0, len(targets), self.batch_size):
            batch = targets[start:start + self.batch_size]
            report = {"targets": [target.root_domain for target in batch], "cost": None, "error": None}
            self.last_batch_reports.append(report)
            try:
                data = await self.client.post(self.endpoint, [{"targets": [target.root_domain for target in batch]}])
            except Exception as exc:
                report["error"] = str(exc)[:2000]
                raise
            task = (data.get("tasks") or [{}])[0]
            task_result = (task.get("result") or [{}])[0]
            items = task_result.get("items") or []
            report.update({"cost": task.get("cost", data.get("cost")), "data": data})
            by_target = {}
            for item in items:
                item_target = item.get("target") or item.get("url")
                if item_target:
                    by_target[root_domain(str(item_target)) or str(item_target).lower()] = item
            for target in batch:
                item = by_target.get(target.root_domain.lower()) or {}
                core_fields = ("rank", "main_domain_rank", "backlinks", "referring_domains", "referring_main_domains", "referring_ips", "referring_subnets")
                mapping_status = "mapped" if any(item.get(field) is not None for field in core_fields) else "provider_missing_or_empty"
                output.append(BacklinkFeatureResult(
                    target=target.root_domain,
                    rank=item.get("rank") or item.get("main_domain_rank"),
                    backlinks=item.get("backlinks"),
                    referring_domains=item.get("referring_domains"),
                    referring_main_domains=item.get("referring_main_domains"),
                    referring_ips=item.get("referring_ips"),
                    referring_subnets=item.get("referring_subnets"),
                    referring_domains_nofollow=item.get("referring_domains_nofollow"),
                    referring_main_domains_nofollow=item.get("referring_main_domains_nofollow"),
                    backlinks_spam_score=item.get("backlinks_spam_score"),
                    raw=item or {},
                    actual_cost=task.get("cost", data.get("cost")),
                    api_status_code=task.get("status_code", data.get("status_code")),
                    api_status_message=task.get("status_message", data.get("status_message")),
                    response_raw={"status_code": data.get("status_code"), "status_message": data.get("status_message"), "cost": data.get("cost"), "tasks": data.get("tasks")},
                    mapping_status=mapping_status,
                    mapping_error=None if mapping_status == "mapped" else "No documented core backlink fields found for target in task.result[0].items[]",
                ))
        return output
