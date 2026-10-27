"""Validated additive in-memory fallback overlay for immutable registered sources."""
import copy
import json
from pathlib import Path
from urllib.parse import urlsplit

DEFAULT_POLICY = Path(__file__).resolve().parents[1] / "policy/source_fallbacks_v1.json"


def apply_fallback_overlay(registry, path=DEFAULT_POLICY):
    """Return an *in-memory copy* only; original registry remains byte-identical."""
    original = copy.deepcopy(registry)
    cfg = copy.deepcopy(registry)
    policy = json.loads(Path(path).read_text(encoding="utf-8"))
    entries = cfg.get("explicit_sources") or []
    sources = {x.get("id"): x for x in entries}
    rows = policy.get("sources")
    if (policy.get("schema_version") != 1 or not isinstance(rows, list)
            or {x.get("id") for x in rows} !=
            {"tamemap_nakano", "itabashi_tourism_festival"}
            or len(rows) != 2):
        raise ValueError("unexpected source fallback policy")
    for spec in rows:
        src = sources.get(spec["id"])
        if not src or src.get("required") is not True or src.get("enabled") is not True:
            raise ValueError("protected required source missing from fallback policy: " + spec["id"])
        if not any(spec["original_required_url_must_contain"] in u
                   for u in src.get("search_urls", [])):
            raise ValueError("registered required URL is missing: " + spec["id"])
        if spec.get("publication_approved") is not False:
            raise ValueError("fallback cannot permit event publication")
        urls = spec.get("supplemental_search_urls", [])
        if not isinstance(urls, list) or len(urls) > 2:
            raise ValueError("too many supplemental URLs")
        for url in urls:
            p = urlsplit(url)
            if (p.scheme != "https" or p.hostname != "pc.tamemap.net" or
                    p.path != "/1311401/new_arrival" or p.username or p.password):
                raise ValueError("unapproved supplemental URL")
            if url not in src["search_urls"]:
                src["search_urls"].append(url)
        ids = spec.get("fallback_source_ids", [])
        if not isinstance(ids, list) or any(x not in sources or x == spec["id"] for x in ids):
            raise ValueError("unapproved fallback source ID")
        if ids:
            if ids != ["itabashi_official_festival"]:
                raise ValueError("unexpected official fallback mapping")
            target = sources["itabashi_official_festival"]
            if (target.get("enabled") is not True or target.get("required") is not True
                    or not any("city.itabashi.tokyo.jp/bunka/kanko/matsuri/1006858.html" in u
                               for u in target.get("search_urls", []))):
                raise ValueError("missing official Itabashi source")
            src["fallback_source_ids"] = ids
    if (registry != original or len(entries) != len(original.get("explicit_sources", []))
            or any(x["id"] != y["id"] for x, y in zip(
                cfg["explicit_sources"], original["explicit_sources"]))):
        raise ValueError("original fixed-source registry mutated")
    return cfg
