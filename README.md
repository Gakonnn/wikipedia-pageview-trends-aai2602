# Wikipedia Pageview Trends

Final project, Programming for Data Analysis and Database. Topic 6, AAI-2602.

Repository: https://github.com/Gakonnn/wikipedia-pageview-trends-aai2602

Team: **Tugelbayev Galymzhan, Dias Ilyas, Zhasulan Aidos** (all AAI-2602).

## Research question

How do Wikipedia pageviews differ between Kazakh, Russian and English, which of six selected topics attract attention, and can simple methods predict the next day's project traffic?

The interface, report and defense guide are in Russian. The code and data-column names use English.

## Quick start

Python **3.12** was used. Run commands from this repository's root.

```bash
python3 -m venv .venv
source .venv/bin/activate
# Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
python main.py --all
python -m streamlit run app.py
```

Open the address printed by Streamlit (normally http://localhost:8501). The first build downloads a 61 MB gzip and small Wikimedia API responses. Network speed determines download time. Allow disk space for raw data, SQLite, Parquet and benchmark CSV. Once prepared, the dashboard works offline.

```bash
python main.py --offline           # rebuild using all cached raw files
python main.py                     # interactive console menu
python -m unittest discover -s tests -v
```

The complete local delivery archive includes prepared data and cached sources. With that archive, after installing dependencies you can launch Streamlit immediately. GitHub excludes large generated files; `--all` reconstructs them. Never mix processed files from different runs.

## Sources and scope

1. [Wikimedia hourly dump](https://dumps.wikimedia.org/other/pageviews/2025/2025-10/pageviews-20251001-120000.gz): complete file, filtered to exact domain codes `en`, `en.m`, `ru`, `ru.m`, `kk`, `kk.m`. Its timestamp is the **end** of the interval: **2025-10-01 11:00–12:00 UTC**. Each selected record is a page/access pair in one hour. This is a cross-sectional snapshot, not a year of hourly data.
2. [Wikimedia Analytics API](https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/): daily counts for **2025-01-01 through 2025-12-31**, `all-access`, `agent=user`. Three whole-project series and 18 article series: six topics × three languages. These support time-series analysis and forecasting. They are kept separate from the hourly snapshot.
3. Wikidata sitelinks map the same six subjects across languages: Kazakhstan (Q232), Almaty (Q35493), Astana (Q1520), artificial intelligence (Q11660), Python (Q28865), Internet (Q75). Cached entity JSON and revisions document the mapping. Current titles may differ from historical titles; redirect counts are not merged.

Exact URLs, byte counts, retrieval timestamps and SHA-256 hashes: `data/raw/manifest.json`. Public analytics datasets are published under CC0; see the [dataset README](https://dumps.wikimedia.org/other/pageviews/readme.html). Code references and methodological sources appear in `docs/SOURCES.md`.

## Processing and quality

- Read the gzip in chunks of 100,000 rows; the whole file is scanned.
- Preserve titles such as `NA` and Unicode text. Do not double URL-decode page titles.
- Validate fields and nonnegative counts. Unexpected parser errors stop processing.
- Use categorical language/access columns and unsigned counts in processing; write compressed Parquet in batches.
- Check unique hourly keys and daily date coverage. Missing dates raise an error, not a fabricated zero.
- Record IQR outliers and retain them: spikes may represent real attention.
- Store normalized data in SQLite with primary keys, foreign keys and indexes.

## Analysis

Descriptive statistics, null/type audits, IQR/boxplots, monthly `resample`, seven-day moving averages, robust STL with period 7, Pearson correlations and six-topic comparisons. Seven static figures and a standalone interactive Plotly HTML accompany the dashboard.

Language is **not** visitor country. Main pages and non-article titles remain in the hourly dataset, which measures page traffic. Selected-topic analysis uses the curated Wikidata mapping. Raw counts describe traffic volume; topic views per million project views help compare relative attention. Correlation does not establish cause.

## Forecast evaluation

Forecast the next day's **whole-project** views separately for `en`, `ru`, `kk`:

- Baseline: previous day's value (`naive`).
- Extra baseline: same weekday last week (`seasonal_naive`).
- Approach 1: average of the seven preceding days.
- Approach 2: linear regression with lag 1/7/14/28, previous 7/28-day averages and sine/cosine weekday features. Negative forecasts are clipped to zero.

Train: January–September (first 28 days build lag history). Validation: October–November (61 days). Test: December (31 days). Choose the method by **validation MAE per language**. Refit regression on train+validation for the test. No shuffling. Each prediction uses only earlier actual observations; this is rolling one-day prediction, **not** a 31-day forecast from November 30.

The complete method table is reported on both splits, but final recommendations use the preselected method. MAE is views/day; compare methods within each language. Do not rank languages by raw MAE. Runtime and peak Python allocations are measured, with limitations documented in `forecast_protocol.json`.

## Storage benchmark

Identical language/access sums on the same filtered hourly rows: full CSV/Pandas (baseline), batched Parquet/Pandas and SQLite/JOIN. Three fresh subprocesses per method; report median processing time and peak process RSS. Totals must match exactly. RSS includes Python/imports; time excludes process startup/imports. OS disk caching is uncontrolled. SQLite size includes its other tables and indexes. The benchmark uses Unix `resource` (macOS/Linux); on Windows run in WSL or skip the benchmark and use the console's preparation/analysis actions.

## Code architecture

| File | Responsibility |
|---|---|
| `main.py` | CLI/menu and pipeline |
| `wiki_trends/acquire.py` | HTTP retries, cache, hashes, source manifest |
| `wiki_trends/prepare.py` | Chunk parsing, typing, quality audit, Parquet |
| `wiki_trends/database.py` | SQLite creation, query loading, results to Pandas |
| `wiki_trends/analyze.py` | EDA, figures, STL, correlations |
| `wiki_trends/forecast.py` | Past-only features and chronological model evaluation |
| `wiki_trends/benchmark.py` | Equal-result time/memory comparisons |
| `app.py` | Streamlit filters, plots, search, SQL viewer and CSV export |
| `sql/` | Normalized schema and ten SQL queries |
| `tests/` | Data integrity, leakage and metric checks |

## Team responsibilities

Agreed division of work and defense preparation:

- **Tugelbayev Galymzhan (AAI-2602):** acquisition, Python pipeline, cleaning and reproducibility.
- **Dias Ilyas (AAI-2602):** SQLite schema, ER diagram, SQL queries and integrity checks.
- **Zhasulan Aidos (AAI-2602):** visualizations, forecasting and dashboard.
- **Joint:** checking conclusions, written report, presentation and rehearsal.

This is a responsibility plan confirmed by the team representative, not a record of individually verified completed work. Before submission, each member should validate their section and the team should update the contribution statement to reflect actual work. Each member must understand the whole project. Initial implementation and explanatory materials were prepared with AI assistance; the team is responsible for verification and following the course's disclosure rules.

## Submission

The report is under `output/pdf/` in the complete archive. The presentation is available in the saved presentation viewer and can be downloaded there as PPTX. GitHub: https://github.com/Gakonnn/wikipedia-pageview-trends-aai2602 . The topic-approval table and Moodle are separate external steps; this local project does not claim either was submitted.


Report rebuild (optional): `python tools/build_report.py`. The script uses the DejaVu font bundled with matplotlib. The saved report and slide deck use the measured results from this run.
