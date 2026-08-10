import re
from pathlib import Path
import tldextract


_TLD_EXTRACT = tldextract.TLDExtract(
    cache_dir=str(Path(__file__).resolve().parents[3] / ".tld-cache"),
    suffix_list_urls=(),
)


def normalize_keyword(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def build_keyword(service_term: str, city: str, state_code: str) -> str:
    return normalize_keyword(f"{service_term} {city} {state_code}")


def root_domain(url: str) -> str:
    e = _TLD_EXTRACT(url)
    return ".".join(p for p in [e.domain, e.suffix] if p)
