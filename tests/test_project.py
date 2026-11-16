import json
import sqlite3
import unittest
import numpy as np
import pandas as pd
from wiki_trends.forecast import lag_features,predict_method
from wiki_trends.prepare import optimize_chunk
from wiki_trends.config import DB,PROCESSED,RESULTS
from wiki_trends.database import load_queries

class ProjectTests(unittest.TestCase):
    def test_features_do_not_see_present_or_future(self):
        s=pd.Series(np.arange(80.),index=pd.date_range('2025-01-01',periods=80))
        changed=s.copy();changed.iloc[50:]=99999
        a,b=lag_features(s),lag_features(changed)
        pd.testing.assert_frame_equal(a.loc[:s.index[50]].drop(columns='y'),b.loc[:s.index[50]].drop(columns='y'))

    def test_naive_and_seasonal_values(self):
        s=pd.Series(np.arange(60.),index=pd.date_range('2025-01-01',periods=60))
        f=lag_features(s);evaluation=f.index==s.index[40];training=f.index<s.index[40]
        self.assertEqual(predict_method('naive',f,training,evaluation)[0],39)
        self.assertEqual(predict_method('seasonal_naive',f,training,evaluation)[0],33)

    def test_optimization_preserves_title_and_counts(self):
        frame=pd.DataFrame({'domain':['en','kk.m'],'title':['NA','Қазақстан'],'views':[100,2]})
        result=optimize_chunk(frame)
        self.assertEqual(result.title.tolist(),['NA','Қазақстан'])
        self.assertEqual(result.views.sum(),102)
        self.assertEqual(result.access.tolist(),['desktop','mobile'])

    def test_database_and_data_agree(self):
        with sqlite3.connect(DB) as con:
            self.assertEqual(con.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            self.assertEqual(con.execute('PRAGMA foreign_key_check').fetchall(),[])
            count=con.execute('SELECT COUNT(*) FROM hourly_views').fetchone()[0]
            self.assertGreaterEqual(count,500_000)
            for sql in load_queries().values(): self.assertGreater(len(pd.read_sql_query(sql,con)),0)
            db=pd.read_sql_query('SELECT language,SUM(views) views FROM project_daily GROUP BY language',con).set_index('language').views
        daily=pd.read_parquet(PROCESSED/'daily.parquet')
        actual=daily[daily.topic_id.eq('__total__')].groupby('language').views.sum()
        self.assertEqual(db.to_dict(),actual.to_dict())

    def test_forecast_metrics_recompute(self):
        metrics=pd.read_csv(RESULTS/'forecast_metrics.csv')
        pred=pd.read_csv(RESULTS/'forecast_predictions.csv')
        for row in metrics.itertuples():
            g=pred[(pred.language==row.language)&(pred.split==row.split)&(pred.method==row.method)]
            self.assertAlmostEqual(float(abs(g.actual-g.predicted).mean()),row.mae,places=5)
            self.assertEqual(len(g),61 if row.split=='validation' else 31)

if __name__=='__main__': unittest.main()
