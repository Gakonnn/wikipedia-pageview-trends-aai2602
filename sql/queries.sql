-- name: 01_hourly_language_access
SELECT p.language,h.access,COUNT(*) AS records,SUM(h.views) AS views
FROM hourly_views h JOIN pages p USING(page_id)
GROUP BY p.language,h.access ORDER BY p.language,h.access;

-- name: 02_top_hourly_pages
WITH totals AS (
 SELECT p.language,p.title,SUM(h.views) AS views
 FROM hourly_views h JOIN pages p USING(page_id) GROUP BY p.page_id
), ranked AS (
 SELECT *,ROW_NUMBER() OVER(PARTITION BY language ORDER BY views DESC,title) AS rank
 FROM totals)
SELECT * FROM ranked WHERE rank<=10 ORDER BY language,rank;

-- name: 03_monthly_totals
SELECT language,substr(date,1,7) AS month,SUM(views) AS views
FROM project_daily GROUP BY language,month ORDER BY language,month;

-- name: 04_topic_popularity
SELECT d.language,t.name AS topic,t.category,SUM(d.views) AS views
FROM topic_daily d JOIN topics t USING(topic_id)
GROUP BY d.language,d.topic_id HAVING SUM(d.views)>0 ORDER BY d.language,views DESC;

-- name: 05_rolling_average
SELECT language,date,views,
 AVG(views) OVER(PARTITION BY language ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS ma7
FROM project_daily ORDER BY language,date;

-- name: 06_day_change
WITH previous AS (SELECT *,LAG(views) OVER(PARTITION BY language ORDER BY date) AS previous_views
 FROM project_daily)
SELECT *,ROUND(100.0*(views-previous_views)/NULLIF(previous_views,0),2) AS change_pct
FROM previous ORDER BY language,date;

-- name: 07_above_average_days
SELECT d.* FROM project_daily d
WHERE views>(SELECT AVG(x.views) FROM project_daily x WHERE x.language=d.language)
ORDER BY language,date;

-- name: 08_topic_share
SELECT d.date,d.language,t.name AS topic,d.views,p.views AS project_views,
 1000000.0*d.views/NULLIF(p.views,0) AS views_per_million
FROM topic_daily d JOIN topics t USING(topic_id)
JOIN project_daily p ON p.language=d.language AND p.date=d.date
ORDER BY d.language,t.name,d.date;

-- name: 09_weekday_pattern
SELECT language,strftime('%w',date) AS weekday,AVG(views) AS mean_views,COUNT(*) AS days
FROM project_daily GROUP BY language,weekday ORDER BY language,weekday;

-- name: 10_topic_mapping
SELECT t.topic_id,t.name,t.category,m.language,p.title
FROM topics t JOIN topic_pages m USING(topic_id) JOIN pages p USING(page_id)
ORDER BY t.name,m.language;
