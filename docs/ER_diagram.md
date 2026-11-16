# SQLite ER diagram

```mermaid
erDiagram
  languages ||--o{ pages : contains
  languages ||--o{ project_daily : measures
  topics ||--o{ topic_pages : maps
  languages ||--o{ topic_pages : translates
  pages ||--o{ topic_pages : identifies
  pages ||--o{ hourly_views : counts
  topic_pages ||--o{ topic_daily : measures
  languages { TEXT language PK }
  pages { INTEGER page_id PK
          TEXT language FK
          TEXT title }
  topics { TEXT topic_id PK
           TEXT name
           TEXT category }
  topic_pages { TEXT topic_id PK,FK
                TEXT language PK,FK
                INTEGER page_id FK }
  hourly_views { INTEGER page_id PK,FK
                 TEXT hour_end PK
                 TEXT access PK
                 INTEGER views }
  project_daily { TEXT language PK,FK
                  TEXT date PK
                  INTEGER views }
  topic_daily { TEXT topic_id PK,FK
                TEXT language PK,FK
                TEXT date PK
                INTEGER views }
```

`pages` has a unique `(language,title)` key. `topic_daily` references the composite `(topic_id,language)` key in `topic_pages`. The three fact tables have different grains and are never concatenated. Access and timestamps describe public aggregated counts, not identifiable people.
