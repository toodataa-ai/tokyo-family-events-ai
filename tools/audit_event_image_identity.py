#!/usr/bin/env python3
"""Fail-closed audit for unrelated events sharing a specific thumbnail on a shared source page.

A news/calendar article can contain several events. An article-level OG image or
the first body image is not evidence that a given image belongs to every event.
This audit compares images across each *published* weekend, using the same
verification overrides the website applies. Generic site logos are reported
as weak thumbnails but are not treated as proof of a mismatched event poster.
"""
import argparse
import json
import pathlib
import re
import sys
from collections import defaultdict
from urllib.parse import urlsplit, urlunsplit

from validate_data import load_week, merge_corrections

GENERIC_IMAGE_RE = re.compile(
    r"(?:^|[/_.-])(?:ogp|ogimage|logo|favicon|placeholder|noimage|no-image|"
    r"default|sns|site-logo|brand-logo)(?:[/_.-]|$)|/common/meta/",
    re.I,
)


def canonical_url(url):
    if not url:
        return ""
    u = urlsplit(str(url).strip())
    if u.scheme not in ("http", "https") or not u.netloc:
        return ""
    return urlunsplit((u.scheme.lower(), u.netloc.lower().removeprefix("www."),
                       u.path.rstrip("/") or "/", "", ""))


def is_generic_image(url):
    return bool(GENERIC_IMAGE_RE.search(urlsplit(url or "").path))


def inspect_events(events, week="unknown"):
    errors, warnings = [], []
    groups = defaultdict(list)
    for ev in events:
        if not isinstance(ev, dict):
            continue
        image = canonical_url(ev.get("image"))
        page = canonical_url(ev.get("official_url") or ev.get("url") or ev.get("source"))
        if image and page:
            groups[(page, image)].append(ev)

    for (page, image), rows in groups.items():
        distinct = {re.sub(r"\s+", "", str(e.get("name") or "")).lower()
                    for e in rows if e.get("name")}
        if len(distinct) < 2:
            continue
        names = " / ".join(sorted({str(e.get("name")) for e in rows}))
        ids = ", ".join(str(e.get("id")) for e in rows)
        if is_generic_image(image):
            warnings.append(
                f"{week}: shared generic site image (review event-specific thumbnails): "
                f"{names}; ids={ids}; image={image}"
            )
        else:
            errors.append(
                f"{week}: EVENT_IMAGE_COLLISION: different events on the same source "
                f"reuse one event-specific image: {names}; ids={ids}; "
                f"image={image}; source={page}"
            )
    return errors, warnings


def audit(data_dir):
    errors, warnings = [], []
    manifest_path = data_dir / "manifest.json"
    if not manifest_path.is_file():
        return [f"missing manifest: {manifest_path}"], []
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for week in manifest.get("weekends", []):
        path = data_dir / week["file"]
        data, rows, failures = load_week(path)
        errors.extend(failures)
        vname = data.get("verification_file")
        if vname:
            vpath = data_dir / vname
            audit_doc = json.loads(vpath.read_text(encoding="utf-8"))
            by_id = {v.get("id"): v.get("corrections") or {}
                     for v in audit_doc.get("events", []) if isinstance(v, dict)}
            rows = [merge_corrections(ev, by_id.get(ev.get("id")))
                    if isinstance(ev, dict) else ev for ev in rows]
        e, w = inspect_events(rows, data.get("sat") or week["file"])
        errors.extend(e)
        warnings.extend(w)
    return errors, warnings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("data_dir", nargs="?", type=pathlib.Path,
                        default=pathlib.Path("site/data"))
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    errors, warnings = audit(args.data_dir)
    for message in warnings:
        print("WARN:", message)
    for message in errors:
        print("ERROR:", message)
    if errors and args.strict:
        print(f"EVENT_IMAGE_AUDIT_FAILED: {len(errors)} collision(s)")
        return 1
    print(f"EVENT_IMAGE_AUDIT: {len(errors)} collision(s), {len(warnings)} weak/shared image(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
