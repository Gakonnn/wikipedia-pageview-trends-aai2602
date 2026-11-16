# Requirement mapping

| Requirement | Implementation / evidence |
|---|---|
| 5+ functions besides main | acquire, prepare, database, analyze, forecast, benchmark modules |
| list / dict | TOPICS, LANGUAGES, metrics, source manifest, menu actions |
| if / elif / else | main.menu, forecast.predict_method |
| loops | chunks, API pages, SQL queries, experiment grids |
| persistent files | gzip/JSON input, CSV/Parquet/SQLite output |
| try / except | acquisition, safe database rebuild, console errors |
| interactive interface | Streamlit filters, page search, SQL selector, CSV download; console menu |
| modularity / standard library | 7 package modules, pathlib, json, sqlite3, datetime, subprocess |
| baseline + 2 approaches | naive + moving average + regression; extra seasonal naive; CSV/Parquet/SQLite benchmark |
| SQL | 7 normalized tables, ER diagram, ten queries including JOIN, HAVING, CTE, windows |
| large data | 6,787,398 source rows, 2,723,008 filtered rows; chunked processing |
| EDA | data audits, types, describe, IQR flags and boxplots |
| time series | daily series, monthly resample, rolling mean, weekly robust STL |
| correlation | Pearson levels heatmap plus change correlations |
| 4-5 charts incl interactive | 7 static PNG figures, Plotly HTML and interactive dashboard |
| SQLite cleaned data | all filtered hourly and all daily observations in normalized tables |
| forecast MAE | chronological train/validation/test, next-day evaluation per language |
| time and memory | three-run storage benchmark; forecast time and Python allocation peak |
| requirements | exact library versions in requirements.txt |
| report | output/pdf/Final_Project_Wikipedia_Trends_AAI-2602_Report.pdf |
| presentation | saved presentation, downloadable PPTX from viewer |
| team roles | README and report; roles confirmed as a responsibility plan |
| defense preparation | docs/Defense_RU.txt |

External steps: verify instructor topic approval, add names to the topic table, submit report/presentation to Moodle. These are not marked completed by local code.

GitHub repository: https://github.com/Gakonnn/wikipedia-pageview-trends-aai2602
