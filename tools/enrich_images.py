#!/usr/bin/env python3
import argparse
import concurrent.futures
import html
import json
import pathlib
import re
import sys
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen

META_TAG_RE = re.compile(r'<meta\b[^>]*>', re.I)
LINK_TAG_RE = re.compile(r'<link\b[^>]*>', re.I)
ATTR_RE = re.compile(r'([:\w-]+)\s*=\s*(["\'])(.*?)\2', re.I | re.S)
JSON_IMAGE_RE = re.compile(r'["\']image["\']\s*:\s*["\']([^"\']+)["\']', re.I)
MAX_BYTES = 2_000_000
TIMEOUT = 12
USER_AGENT = 'Mozilla/5.0 (compatible; TokyoFamilyEventsAI/1.0; +https://toodataa-ai.github.io/tokyo-family-events-ai/)'


def is_http(value):
    return isinstance(value, str) and value.startswith(('http://', 'https://'))


def attrs(tag):
    return {m.group(1).lower(): html.unescape(m.group(3).strip()) for m in ATTR_RE.finditer(tag)}


def normalize_image_url(base_url, value):
    if not value:
        return None
    value = html.unescape(value.strip())
    if value.startswith('data:'):
        return None
    resolved = urljoin(base_url, value)
    try:
        p = urlsplit(resolved)
        if p.scheme not in ('http', 'https') or not p.netloc:
            return None
    except Exception:
        return None
    return resolved


def extract_image(base_url, text):
    priorities = {
        'og:image': 1,
        'og:image:secure_url': 1,
        'twitter:image': 2,
        'twitter:image:src': 2,
        'image': 3,
    }
    found = []
    for tag in META_TAG_RE.findall(text):
        a = attrs(tag)
        key = (a.get('property') or a.get('name') or a.get('itemprop') or '').lower()
        if key in priorities and a.get('content'):
            u = normalize_image_url(base_url, a['content'])
            if u:
                found.append((priorities[key], u))
    if found:
        found.sort(key=lambda x: x[0])
        return found[0][1]

    for tag in LINK_TAG_RE.findall(text):
        a = attrs(tag)
        rel = (a.get('rel') or '').lower()
        if 'image_src' in rel and a.get('href'):
            u = normalize_image_url(base_url, a['href'])
            if u:
                return u

    m = JSON_IMAGE_RE.search(text)
    if m:
        u = normalize_image_url(base_url, m.group(1).replace('\\/', '/'))
        if u:
            return u
    return None


def fetch_image_from_page(url):
    if not is_http(url):
        return None
    if urlsplit(url).path.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png', '.webp', '.gif')):
        return url if urlsplit(url).path.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif')) else None
    req = Request(url, headers={
        'User-Agent': USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ja,en-US;q=0.7,en;q=0.5',
    })
    try:
        with urlopen(req, timeout=TIMEOUT) as resp:
            ctype = (resp.headers.get('Content-Type') or '').lower()
            final_url = resp.geturl()
            if ctype.startswith('image/'):
                return final_url
            if 'html' not in ctype and 'xml' not in ctype and ctype:
                return None
            raw = resp.read(MAX_BYTES)
            charset = resp.headers.get_content_charset() or 'utf-8'
            try:
                text = raw.decode(charset, errors='replace')
            except LookupError:
                text = raw.decode('utf-8', errors='replace')
            return extract_image(final_url, text)
    except Exception:
        return None


def candidate_pages(ev):
    out = []
    for key in ('official_url', 'url', 'source'):
        u = ev.get(key)
        if is_http(u) and u not in out:
            out.append(u)
    return out


def enrich_event(ev, cache):
    if is_http(ev.get('image')):
        return False, ev.get('image')
    for page in candidate_pages(ev):
        if page not in cache:
            cache[page] = fetch_image_from_page(page)
        if cache[page]:
            ev['image'] = cache[page]
            return True, cache[page]
    return False, None


def load_event_files(data_dir):
    return sorted(data_dir.glob('*-events-*.json'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('data_dir', type=pathlib.Path)
    ap.add_argument('--workers', type=int, default=8)
    args = ap.parse_args()

    files = load_event_files(args.data_dir)
    if not files:
        print('No event shard files found; nothing to enrich.')
        return 0

    datasets = []
    all_events = []
    for path in files:
        data = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(data, list):
            print(f'ERROR: {path} must contain an array')
            return 2
        datasets.append((path, data))
        all_events.extend(data)

    unresolved = [ev for ev in all_events if not is_http(ev.get('image'))]
    cache = {}

    def worker(ev):
        local_cache = {}
        changed, image = enrich_event(ev, local_cache)
        return ev.get('id'), changed, image, local_cache

    enriched = 0
    if unresolved:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
            futures = [ex.submit(worker, ev) for ev in unresolved]
            result_by_id = {}
            for fut in concurrent.futures.as_completed(futures):
                eid, changed, image, local_cache = fut.result()
                cache.update(local_cache)
                result_by_id[eid] = (changed, image)
        for ev in unresolved:
            changed, image = result_by_id.get(ev.get('id'), (False, None))
            if changed and image:
                ev['image'] = image
                enriched += 1

    for path, data in datasets:
        path.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')

    total = len(all_events)
    with_image = sum(1 for ev in all_events if is_http(ev.get('image')))
    coverage = (with_image / total) if total else 1.0
    print(f'Thumbnail enrichment: {with_image}/{total} ({coverage:.1%}), newly enriched={enriched}')
    missing = [ev.get('id') for ev in all_events if not is_http(ev.get('image'))]
    if missing:
        print('No thumbnail metadata found:', ', '.join(x for x in missing if x))
    return 0


if __name__ == '__main__':
    sys.exit(main())
