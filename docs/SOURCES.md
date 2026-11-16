# Sources

- Wikimedia hourly pageview files: https://dumps.wikimedia.org/other/pageviews/
- Dataset format, UTC interval end, domain encoding: https://wikitech.wikimedia.org/wiki/Data_Platform/Data_Lake/Traffic/Pageviews
- Analytics data and CC0: https://dumps.wikimedia.org/other/pageviews/readme.html
- Analytics API: https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/
- Pageview definition and redirect limitations: https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/concepts/page-views.html
- Wikidata entities and sitelinks: https://www.wikidata.org/wiki/Wikidata:Data_access
- pandas chunk reader: https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html
- statsmodels STL: https://www.statsmodels.org/stable/generated/statsmodels.tsa.seasonal.STL.html
- sklearn LinearRegression: https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LinearRegression.html
- SQLite window functions: https://www.sqlite.org/windowfunctions.html

Raw source URLs and SHA-256 checksums are recorded in `data/raw/manifest.json`. Libraries are listed with exact tested versions in `requirements.txt`. Original project code was prepared with AI assistance; external documentation informs API use and data interpretation.
