import json
import re
import sqlite3
import pandas as pd
import pyarrow.parquet as pq
from .config import ROOT, RAW, DB, PROCESSED, RESULTS, LANGUAGES, TOPICS, HOUR_END

def connect():
    con = sqlite3.connect(DB)
    con.execute('PRAGMA foreign_keys=ON')
    return con

def build_database():
    # Build next to the existing DB. A failed build preserves the old working file.
    temporary = DB.with_suffix('.building.db')
    temporary.unlink(missing_ok=True)
    con = sqlite3.connect(temporary)
    try:
        con.executescript((ROOT / 'sql/schema.sql').read_text())
        con.executemany('INSERT INTO languages VALUES (?,?)', LANGUAGES.items())
        con.executemany('INSERT INTO topics VALUES (?,?,?)', TOPICS)
        con.execute('CREATE TABLE staging(language TEXT,access TEXT,title TEXT,views INTEGER)')
        for batch in pq.ParquetFile(PROCESSED / 'hourly.parquet').iter_batches(batch_size=100_000):
            con.executemany('INSERT INTO staging VALUES (?,?,?,?)', batch.to_pandas().itertuples(index=False,name=None))
        counts = con.execute('SELECT COUNT(*) FROM staging').fetchone()[0]
        unique = con.execute('SELECT COUNT(*) FROM (SELECT language,access,title FROM staging GROUP BY 1,2,3)').fetchone()[0]
        if counts != unique:
            raise ValueError('Duplicate hourly keys detected; inspect source before aggregation')
        con.execute('INSERT INTO pages(language,title) SELECT DISTINCT language,title FROM staging')
        con.execute('INSERT INTO hourly_views SELECT p.page_id,?,s.access,s.views FROM staging s '
                    'JOIN pages p ON p.language=s.language AND p.title=s.title', (HOUR_END,))
        con.execute('DROP TABLE staging')
        mappings = json.loads((RAW / 'topic_mapping.json').read_text())
        for item in mappings:
            title = item['title'].replace(' ', '_')
            con.execute('INSERT OR IGNORE INTO pages(language,title) VALUES (?,?)',(item['language'],title))
            pid = con.execute('SELECT page_id FROM pages WHERE language=? AND title=?',(item['language'],title)).fetchone()[0]
            con.execute('INSERT INTO topic_pages VALUES (?,?,?)',(item['topic_id'],item['language'],pid))
        daily = pd.read_parquet(PROCESSED / 'daily.parquet')
        for row in daily.itertuples(index=False):
            date = row.date.strftime('%Y-%m-%d')
            if row.topic_id == '__total__':
                con.execute('INSERT INTO project_daily VALUES (?,?,?)',(row.language,date,row.views))
            else:
                con.execute('INSERT INTO topic_daily VALUES (?,?,?,?)',(row.topic_id,row.language,date,row.views))
        con.commit()
        if con.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('Broken database references')
        con.execute('VACUUM')
        con.close()
        temporary.replace(DB)
    except Exception:
        con.close()
        temporary.unlink(missing_ok=True)
        raise
    return dict(hourly_rows=counts, duplicate_keys=counts-unique)

def load_queries():
    text = (ROOT / 'sql/queries.sql').read_text()
    return {name:sql.strip() for name,sql in re.findall(r'-- name: (\w+)\n(.*?)(?=-- name:|\Z)',text,re.S)}

def run_queries():
    outputs = {}
    with connect() as con:
        for name,sql in load_queries().items():
            frame = pd.read_sql_query(sql,con)
            frame.to_csv(RESULTS / 'sql' / f'{name}.csv',index=False)
            outputs[name] = len(frame)
    return outputs
