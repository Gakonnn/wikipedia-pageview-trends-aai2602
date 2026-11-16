"""Bounded-memory processing of a complete Wikimedia gzip file."""
import json
from time import perf_counter
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from .config import RAW, PROCESSED, RESULTS, DUMP_URL, HOUR_END, LANGUAGES

def optimize_chunk(frame):
    frame = frame.copy()
    frame['language'] = frame['domain'].str.split('.').str[0].astype('category')
    frame['access'] = frame['domain'].str.endswith('.m').map({True: 'mobile', False: 'desktop'}).astype('category')
    frame['views'] = pd.to_numeric(frame['views'], downcast='unsigned')
    return frame[['language', 'access', 'title', 'views']]

def prepare_hourly(chunksize=100_000):
    source = RAW / DUMP_URL.rsplit('/', 1)[-1]
    domains = {code + suffix for code in LANGUAGES for suffix in ['', '.m']}
    output = PROCESSED / 'hourly.parquet'
    partial = output.with_suffix('.parquet.part')
    schema = pa.schema([('language', pa.string()), ('access', pa.string()),
                        ('title', pa.string()), ('views', pa.uint64())])
    audit = dict(source_rows=0, selected_rows=0, invalid_selected=0,
                 max_chunk_rows=0, max_raw_chunk_bytes=0, max_optimized_chunk_bytes=0,
                 hour_end_utc=HOUR_END, hour_start_utc='2025-10-01T11:00:00Z')
    started = perf_counter()
    try:
        with pq.ParquetWriter(partial, schema, compression='zstd') as writer:
            for raw in pd.read_csv(source, sep=' ', header=None,
                    names=['domain', 'title', 'views', 'unused_bytes'],
                    dtype={'domain':'string', 'title':'string', 'views':'int64', 'unused_bytes':'int64'},
                    chunksize=chunksize, keep_default_na=False, on_bad_lines='error'):
                audit['source_rows'] += len(raw)
                audit['max_chunk_rows'] = max(audit['max_chunk_rows'], len(raw))
                selected = raw[raw['domain'].isin(domains)].copy()
                valid = selected['title'].ne('') & selected['views'].ge(0)
                audit['invalid_selected'] += int((~valid).sum())
                selected = selected.loc[valid]
                if selected.empty:
                    continue
                before = int(selected.memory_usage(deep=True).sum())
                cleaned = optimize_chunk(selected)
                after = int(cleaned.memory_usage(deep=True).sum())
                audit['max_raw_chunk_bytes'] = max(audit['max_raw_chunk_bytes'], before)
                audit['max_optimized_chunk_bytes'] = max(audit['max_optimized_chunk_bytes'], after)
                writer.write_table(pa.Table.from_pandas(cleaned, schema=schema, preserve_index=False))
                audit['selected_rows'] += len(cleaned)
                if audit['source_rows'] % 1_000_000 == 0:
                    print('Parsed rows:', audit['source_rows'], flush=True)
        partial.replace(output)
    except Exception:
        partial.unlink(missing_ok=True)
        raise
    audit['processing_seconds'] = perf_counter() - started
    audit['gzip_bytes'] = source.stat().st_size
    audit['parquet_bytes'] = output.stat().st_size
    (RESULTS / 'hourly_audit.json').write_text(json.dumps(audit, indent=2))
    return audit

def prepare_daily():
    mappings = json.loads((RAW / 'topic_mapping.json').read_text())
    rows = []
    specs = [(f'daily_total_{lang}.json', lang, '__total__', 'All pages', 'All pages') for lang in LANGUAGES]
    specs += [(f"daily_{x['topic_id']}_{x['language']}.json", x['language'], x['topic_id'], x['topic'], x['category']) for x in mappings]
    for filename, lang, topic_id, topic, category in specs:
        for item in json.loads((RAW / filename).read_text())['items']:
            rows.append(dict(date=pd.to_datetime(item['timestamp'][:8], format='%Y%m%d'),
                language=lang, topic_id=topic_id, topic=topic, category=category, views=item['views']))
    df = pd.DataFrame(rows).sort_values(['language','topic_id','date']).reset_index(drop=True)
    if df.duplicated(['date','language','topic_id']).any() or df['views'].lt(0).any():
        raise ValueError('Invalid daily records or duplicate keys')
    expected = pd.date_range('2025-01-01', '2025-12-31')
    gaps = []
    for (lang, topic), g in df.groupby(['language','topic_id']):
        for date in expected.difference(g['date']):
            gaps.append(dict(language=lang, topic_id=topic, missing_date=str(date.date())))
    # Missing observations are never silently replaced with zero.
    (RESULTS / 'daily_audit.json').write_text(json.dumps(dict(rows=len(df), missing_dates=gaps,
        duplicate_keys=0, missing_cells=int(df.isna().sum().sum()), min_views=int(df.views.min())), indent=2))
    if gaps:
        raise ValueError(f'{len(gaps)} missing days: inspect daily_audit.json')
    df.to_parquet(PROCESSED / 'daily.parquet', index=False)
    df.to_csv(PROCESSED / 'daily.csv', index=False)
    return df
