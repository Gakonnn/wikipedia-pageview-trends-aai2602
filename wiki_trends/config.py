from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data' / 'raw'
PROCESSED = ROOT / 'data' / 'processed'
RESULTS = ROOT / 'results'
DB = PROCESSED / 'wikipedia.db'
LANGUAGES = {'kk': 'Қазақша', 'ru': 'Русский', 'en': 'English'}
DUMP_URL = ('https://dumps.wikimedia.org/other/pageviews/2025/2025-10/'
            'pageviews-20251001-120000.gz')
# Wikimedia filename denotes the END of the hourly interval, in UTC.
HOUR_END = '2025-10-01T12:00:00Z'
TOPICS = [
    ('Q232', 'Kazakhstan', 'Geography'),
    ('Q35493', 'Almaty', 'Cities'),
    ('Q1520', 'Astana', 'Cities'),
    ('Q11660', 'Artificial intelligence', 'Technology'),
    ('Q28865', 'Python', 'Technology'),
    ('Q75', 'Internet', 'Technology'),
]
START, END = '2025010100', '2025123100'
USER_AGENT = 'WikipediaTrendsStudentProject/1.0 (educational reproducible analysis)'

def ensure_directories():
    for path in [RAW, PROCESSED, RESULTS / 'sql', RESULTS / 'figures']:
        path.mkdir(parents=True, exist_ok=True)
