"""Same group-by on the same filtered rows; fresh processes, 3 repetitions."""
import json
import sqlite3
import subprocess
import sys
from time import perf_counter
import pandas as pd
import pyarrow.parquet as pq
from .config import ROOT, PROCESSED, RESULTS, DB

def peak_memory_mib():
    """Peak resident memory of this process on Windows, macOS and Linux."""
    if sys.platform=='win32':
        import psutil  # Windows: peak working set (resource module does not exist).
        return psutil.Process().memory_info().peak_wset/1024**2
    import resource
    # ru_maxrss: bytes on macOS, KiB on Linux. Includes interpreter/imports.
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return rss/(1024**2 if sys.platform=='darwin' else 1024)

def worker(method):
    start=perf_counter()
    if method=='csv_full':
        frame=pd.read_csv(PROCESSED/'hourly.csv')
        result=frame.groupby(['language','access']).views.sum()
    elif method=='parquet_chunks':
        sums={}
        for batch in pq.ParquetFile(PROCESSED/'hourly.parquet').iter_batches(batch_size=100_000):
            partial=batch.to_pandas().groupby(['language','access']).views.sum()
            for key,value in partial.items(): sums[key]=sums.get(key,0)+int(value)
        result=pd.Series(sums)
    elif method=='sqlite':
        with sqlite3.connect(DB) as con:
            df=pd.read_sql_query('SELECT p.language,h.access,SUM(h.views) views FROM hourly_views h JOIN pages p USING(page_id) GROUP BY p.language,h.access',con)
        result=df.set_index(['language','access']).views
    else:
        raise ValueError(method)
    elapsed=perf_counter()-start
    return dict(method=method,seconds=elapsed,peak_rss_mib=peak_memory_mib(),
                totals={':'.join(k):int(v) for k,v in result.items()})

def benchmark():
    first=True
    for batch in pq.ParquetFile(PROCESSED/'hourly.parquet').iter_batches(batch_size=100_000):
        batch.to_pandas().to_csv(PROCESSED/'hourly.csv',mode='w' if first else 'a',header=first,index=False)
        first=False
    rows=[]; expected=None
    for repeat in range(3):
        for method in ['csv_full','parquet_chunks','sqlite']:
            output=subprocess.check_output([sys.executable,'-m','wiki_trends.benchmark',method],text=True,cwd=ROOT)
            row=json.loads(output)
            totals=row.pop('totals')
            if expected is None: expected=totals
            if totals!=expected: raise AssertionError('Benchmark results differ')
            row['repeat']=repeat+1;rows.append(row)
    pd.DataFrame(rows).to_csv(RESULTS/'storage_benchmark_runs.csv',index=False)
    summary=pd.DataFrame(rows).groupby('method')[['seconds','peak_rss_mib']].median().reset_index()
    sizes={'csv_full':PROCESSED/'hourly.csv','parquet_chunks':PROCESSED/'hourly.parquet','sqlite':DB}
    summary['file_mib']=summary.method.map(lambda m:sizes[m].stat().st_size/1024**2)
    summary.to_csv(RESULTS/'storage_benchmark.csv',index=False)
    (RESULTS/'storage_benchmark_protocol.json').write_text(json.dumps(dict(
        repetitions=3,aggregation=expected,quality='Exact equality of language/access sums',
        timing='read+groupby only; excludes imports and process startup; uncontrolled OS cache',
        memory='fresh-process peak RSS including Python and imports (Windows: psutil peak working set)',
        platform=sys.platform,
        size_note='SQLite includes normalized tables, indexes and daily data'),indent=2))
    return summary

if __name__=='__main__':
    print(json.dumps(worker(sys.argv[1])))
