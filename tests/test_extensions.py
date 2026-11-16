"""Tests for the forecasting, SQL and benchmark extensions (Dias Ilyas)."""
import sqlite3
import unittest
import numpy as np
import pandas as pd
from wiki_trends.benchmark import peak_memory_mib
from wiki_trends.config import DB, RESULTS
from wiki_trends.database import load_queries
from wiki_trends.forecast import METHODS, BACKTEST_MONTHS, forecast_scores, lag_features, predict_method

def toy_series(days=120, seed=0):
    rng = np.random.default_rng(seed)
    index = pd.date_range('2025-01-01', periods=days)
    weekly = 1 + 0.2*np.sin(2*np.pi*index.dayofweek/7)
    return pd.Series(1000*weekly + rng.normal(0, 20, days), index=index)

class ForecastExtensionTests(unittest.TestCase):
    def test_learned_models_ignore_target_day_and_future(self):
        s = toy_series()
        changed = s.copy(); changed.iloc[90:] = 10**7
        target = s.index[90]
        for method in ['linear_regression', 'gradient_boosting']:
            preds = []
            for series in (s, changed):
                frame = lag_features(series)
                preds.append(predict_method(method, frame, frame.index < target, frame.index == target)[0])
            self.assertAlmostEqual(preds[0], preds[1], places=6, msg=method)

    def test_gradient_boosting_is_nonnegative_and_reasonable(self):
        frame = lag_features(toy_series())
        evaluation = frame.index >= '2025-04-01'
        pred = predict_method('gradient_boosting', frame, frame.index < '2025-04-01', evaluation)
        self.assertTrue((pred >= 0).all())
        self.assertLess(np.mean(np.abs(pred - frame.loc[evaluation, 'y'])), 150)

    def test_scores_match_hand_calculation(self):
        history = pd.Series([10.]*7 + [12.]*7)  # seasonal naive in-sample MAE = 2
        scores = forecast_scores([10, 20], [12, 16], history)
        self.assertAlmostEqual(scores['mae'], 3)
        self.assertAlmostEqual(scores['rmse'], np.sqrt(10))
        self.assertAlmostEqual(scores['mape'], 20)
        self.assertAlmostEqual(scores['mase'], 1.5)

    def test_saved_metrics_and_backtest_are_complete(self):
        metrics = pd.read_csv(RESULTS / 'forecast_metrics.csv')
        self.assertEqual(set(metrics.method), set(METHODS))
        self.assertTrue({'rmse', 'mape', 'mase'} <= set(metrics.columns))
        folds = pd.read_csv(RESULTS / 'forecast_backtest.csv')
        self.assertEqual(len(folds), 3*len(METHODS)*len(BACKTEST_MONTHS))
        self.assertEqual(set(folds.fold), set(BACKTEST_MONTHS))
        self.assertTrue((folds.groupby(['language', 'fold']).n.nunique() == 1).all())

class SqlAndBenchmarkTests(unittest.TestCase):
    def test_new_queries_use_windows_and_return_rows(self):
        queries = load_queries()
        self.assertGreaterEqual(len(queries), 15)
        expected = {'11_topic_monthly_rank': 'RANK() OVER(', '12_weekend_effect': 'CASE WHEN',
                    '13_topic_peak_days': 'DENSE_RANK() OVER(', '14_cumulative_share': 'SUM(views) OVER(',
                    '15_topic_language_share': 'HAVING'}
        with sqlite3.connect(DB) as con:
            for name, keyword in expected.items():
                self.assertIn(keyword, queries[name])
                self.assertGreater(len(pd.read_sql_query(queries[name], con)), 0, name)
            cumulative = pd.read_sql_query(queries['14_cumulative_share'], con)
        last = cumulative.groupby('language').cumulative_pct.last()
        self.assertTrue(np.allclose(last, 100))

    def test_peak_memory_is_measured_on_this_platform(self):
        self.assertGreater(peak_memory_mib(), 1)

if __name__ == '__main__': unittest.main()
