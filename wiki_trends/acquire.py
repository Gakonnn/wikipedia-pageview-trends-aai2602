"""Resumable by-file downloads with cache, retries and a provenance manifest."""
import hashlib
import json
import time
from datetime import datetime, timezone
from urllib.parse import quote
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from .config import RAW, DUMP_URL, LANGUAGES, TOPICS, START, END, USER_AGENT, ensure_directories

def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def session():
    s = requests.Session()
    s.headers['User-Agent'] = USER_AGENT
    s.mount('https://', HTTPAdapter(max_retries=Retry(
        total=4, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])))
    return s

def fetch(s, url, path):
    manifest_path = RAW / 'manifest.json'
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    previous = manifest.get(path.name)
    if path.exists() and previous and sha256(path) == previous['sha256']:
        return path
    partial = path.with_suffix(path.suffix + '.part')
    try:
        with s.get(url, stream=True, timeout=(20, 120)) as response:
            response.raise_for_status()
            with partial.open('wb') as stream:
                for block in response.iter_content(1024 * 1024):
                    stream.write(block)
        partial.replace(path)
    except (requests.RequestException, OSError):
        partial.unlink(missing_ok=True)
        raise
    manifest[path.name] = dict(url=url, bytes=path.stat().st_size,
        sha256=sha256(path), retrieved_utc=datetime.now(timezone.utc).isoformat())
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print('Downloaded:', path.name, path.stat().st_size, flush=True)
    return path

def download_data():
    ensure_directories()
    s = session()
    fetch(s, DUMP_URL, RAW / DUMP_URL.rsplit('/', 1)[-1])
    mappings = []
    for qid, label, category in TOPICS:
        p = fetch(s, f'https://www.wikidata.org/wiki/Special:EntityData/{qid}.json', RAW / f'{qid}.json')
        entity = json.loads(p.read_text())['entities'][qid]
        for lang in LANGUAGES:
            title = entity['sitelinks'][lang + 'wiki']['title']
            mappings.append(dict(topic_id=qid, topic=label, category=category,
                                 language=lang, title=title, revision=entity['lastrevid']))
    (RAW / 'topic_mapping.json').write_text(json.dumps(mappings, ensure_ascii=False, indent=2))
    base = 'https://wikimedia.org/api/rest_v1/metrics/pageviews'
    for lang in LANGUAGES:
        url = f'{base}/aggregate/{lang}.wikipedia/all-access/user/daily/{START}/{END}'
        fetch(s, url, RAW / f'daily_total_{lang}.json')
    for item in mappings:
        title = quote(item['title'].replace(' ', '_'), safe='')
        url = f"{base}/per-article/{item['language']}.wikipedia/all-access/user/{title}/daily/{START}/{END}"
        fetch(s, url, RAW / f"daily_{item['topic_id']}_{item['language']}.json")
        time.sleep(.1)
    s.close()
