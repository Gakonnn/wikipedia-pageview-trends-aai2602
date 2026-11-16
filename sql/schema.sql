PRAGMA foreign_keys=ON;
CREATE TABLE languages(language TEXT PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE topics(topic_id TEXT PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL);
CREATE TABLE pages(page_id INTEGER PRIMARY KEY, language TEXT NOT NULL REFERENCES languages,
 title TEXT NOT NULL, UNIQUE(language,title));
CREATE TABLE topic_pages(topic_id TEXT REFERENCES topics, language TEXT REFERENCES languages,
 page_id INTEGER NOT NULL REFERENCES pages, PRIMARY KEY(topic_id,language));
CREATE TABLE hourly_views(page_id INTEGER REFERENCES pages, hour_end TEXT NOT NULL,
 access TEXT CHECK(access IN ('desktop','mobile')), views INTEGER NOT NULL CHECK(views>=0),
 PRIMARY KEY(page_id,hour_end,access));
CREATE TABLE project_daily(language TEXT REFERENCES languages, date TEXT NOT NULL,
 views INTEGER NOT NULL CHECK(views>=0), PRIMARY KEY(language,date));
CREATE TABLE topic_daily(topic_id TEXT, language TEXT, date TEXT NOT NULL,
 views INTEGER NOT NULL CHECK(views>=0), PRIMARY KEY(topic_id,language,date),
 FOREIGN KEY(topic_id,language) REFERENCES topic_pages(topic_id,language));
CREATE INDEX idx_pages_language ON pages(language);
CREATE INDEX idx_topic_date ON topic_daily(date);
