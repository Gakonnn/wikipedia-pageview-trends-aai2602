"""One-day-ahead evaluation. Features only use observations before the target day."""
import json
import tracemalloc
from time import perf_counter
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error
from .config import PROCESSED, RESULTS

METHODS = ['naive', 'seasonal_naive', 'moving_average_7', 'linear_regression', 'gradient_boosting']
# Rolling-origin backtest: each month is predicted by a model trained on all earlier days.
BACKTEST_MONTHS = ['2025-07', '2025-08', '2025-09', '2025-10', '2025-11', '2025-12']

def lag_features(series):
    frame = pd.DataFrame({'y':series})
    for lag in [1,7,14,28]:
        frame[f'lag_{lag}'] = series.shift(lag)
    frame['ma7'] = series.shift(1).rolling(7).mean()
    frame['ma28'] = series.shift(1).rolling(28).mean()
    frame['dow_sin'] = np.sin(2*np.pi*frame.index.dayofweek/7)
    frame['dow_cos'] = np.cos(2*np.pi*frame.index.dayofweek/7)
    return frame.dropna()

def relative_features(frame):
    """Scale-free features for trees: each lag divided by the past 7-day mean."""
    rel = pd.DataFrame(index=frame.index)
    for col in ['lag_1','lag_7','lag_14','lag_28','ma28']:
        rel[col] = frame[col]/frame['ma7']
    rel['weekday'] = frame.index.dayofweek
    return rel

def predict_method(method, frame, training, evaluation):
    if method == 'naive':
        return frame.loc[evaluation,'lag_1'].to_numpy()
    elif method == 'seasonal_naive':
        return frame.loc[evaluation,'lag_7'].to_numpy()
    elif method == 'moving_average_7':
        return frame.loc[evaluation,'ma7'].to_numpy()
    elif method == 'linear_regression':
        features = frame.columns.drop('y')
        model = LinearRegression().fit(frame.loc[training,features],frame.loc[training,'y'])
        return np.maximum(model.predict(frame.loc[evaluation,features]),0)
    elif method == 'gradient_boosting':
        # Trees cannot extrapolate beyond training levels, so the model learns the
        # ratio of tomorrow's views to the past 7-day mean and we multiply back.
        rel = relative_features(frame)
        target = frame['y']/frame['ma7']
        model = HistGradientBoostingRegressor(max_iter=200, learning_rate=0.05, max_leaf_nodes=15,
                                              min_samples_leaf=10, categorical_features=[rel.columns.get_loc('weekday')],
                                              random_state=0)
        model.fit(rel.loc[training], target.loc[training])
        return np.maximum(model.predict(rel.loc[evaluation])*frame.loc[evaluation,'ma7'].to_numpy(), 0)
    raise ValueError(f'Unknown method {method}')

def forecast_scores(actual, predicted, training_series):
    """MAE/RMSE in views per day, MAPE in %, MASE scaled by in-sample seasonal naive MAE."""
    actual, predicted = np.asarray(actual, float), np.asarray(predicted, float)
    history = np.asarray(training_series, float)
    scale = np.mean(np.abs(history[7:] - history[:-7]))
    mae = mean_absolute_error(actual, predicted)
    return dict(mae=mae, rmse=float(np.sqrt(mean_squared_error(actual, predicted))),
                mape=float(np.mean(np.abs(actual-predicted)/np.where(actual == 0, np.nan, actual))*100),
                mase=float(mae/scale) if scale else np.nan)

def load_project_series():
    daily = pd.read_parquet(PROCESSED / 'daily.parquet')
    output = {}
    for lang,g in daily[daily.topic_id.eq('__total__')].groupby('language'):
        series = g.set_index('date')['views'].sort_index().asfreq('D').astype(float)
        if series.isna().any():
            raise ValueError('Forecast requires complete daily data')
        output[lang] = series
    return output

def compare_forecasts():
    metrics, predictions, selections = [], [], {}
    for lang, series in load_project_series().items():
        frame = lag_features(series)
        for split in ['validation','test']:
            boundary = '2025-10-01' if split == 'validation' else '2025-12-01'
            finish = '2025-12-01' if split == 'validation' else '2026-01-01'
            training = frame.index < boundary
            evaluation = (frame.index >= boundary) & (frame.index < finish)
            for method in METHODS:
                tracemalloc.start()
                start = perf_counter()
                pred = predict_method(method,frame,training,evaluation)
                seconds = perf_counter()-start
                _,peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                actual = frame.loc[evaluation,'y'].to_numpy()
                metrics.append(dict(language=lang,split=split,method=method,n=len(actual),
                    **forecast_scores(actual,pred,frame.loc[training,'y']),seconds=seconds,python_peak_kib=peak/1024))
                for date,a,p in zip(frame.index[evaluation],actual,pred):
                    predictions.append(dict(language=lang,split=split,method=method,date=date,actual=a,predicted=p))
        val = pd.DataFrame(metrics).query('language == @lang and split == "validation"')
        selections[lang] = val.sort_values(['mae','method']).iloc[0]['method']
    metrics = pd.DataFrame(metrics)
    metrics['selected_on_validation'] = metrics.apply(lambda r: selections[r.language]==r.method,axis=1)
    metrics.to_csv(RESULTS / 'forecast_metrics.csv',index=False)
    predictions = pd.DataFrame(predictions)
    predictions.to_csv(RESULTS / 'forecast_predictions.csv',index=False)
    weekday_errors(predictions, selections).to_csv(RESULTS / 'forecast_errors_by_weekday.csv', index=False)
    (RESULTS / 'forecast_protocol.json').write_text(json.dumps(dict(
        train='2025-01-01..2025-09-30 (first 28 days warm-up)',validation='2025-10-01..2025-11-30',
        test='2025-12-01..2025-12-31', horizon='rolling one day ahead; past actual observations available',
        refit='learned models fitted on train for validation, train+validation for test',
        methods=METHODS,
        metric='MAE in views/day (selection), plus RMSE, MAPE % and MASE (scale: in-sample seasonal naive MAE)',
        memory='tracemalloc peak Python allocations; excludes most native-library memory',
        selection=selections),indent=2))
    return metrics

def weekday_errors(predictions, selections):
    """Error analysis: mean absolute error of the selected method by weekday on the test month."""
    rows = []
    for lang, method in selections.items():
        g = predictions[(predictions.language == lang) & (predictions.split == 'test') & (predictions.method == method)].copy()
        g['weekday'] = pd.to_datetime(g.date).dt.day_name()
        g['abs_error'] = (g.actual-g.predicted).abs()
        g['pct_error'] = g.abs_error/g.actual*100
        for day, d in g.groupby('weekday', sort=False):
            rows.append(dict(language=lang, method=method, weekday=day, days=len(d),
                             mae=d.abs_error.mean(), mean_pct_error=d.pct_error.mean()))
    return pd.DataFrame(rows)

def backtest_forecasts():
    """Robustness check over six monthly folds (expanding window). Not used for model selection."""
    rows = []
    for lang, series in load_project_series().items():
        frame = lag_features(series)
        for month in BACKTEST_MONTHS:
            start = pd.Timestamp(month + '-01')
            training = frame.index < start
            evaluation = frame.index.to_period('M') == pd.Period(month)
            actual = frame.loc[evaluation, 'y'].to_numpy()
            for method in METHODS:
                started = perf_counter()
                pred = predict_method(method, frame, training, evaluation)
                rows.append(dict(language=lang, fold=month, method=method, n=len(actual),
                                 **forecast_scores(actual, pred, frame.loc[training, 'y']),
                                 seconds=perf_counter()-started))
    folds = pd.DataFrame(rows)
    folds['rank'] = folds.groupby(['language','fold']).mae.rank(method='min')
    folds.to_csv(RESULTS / 'forecast_backtest.csv', index=False)
    summary = folds.groupby(['language','method']).agg(mean_mae=('mae','mean'), std_mae=('mae','std'),
        mean_mase=('mase','mean'), mean_rank=('rank','mean'), wins=('rank', lambda r: int((r == 1).sum()))).reset_index()
    summary.to_csv(RESULTS / 'forecast_backtest_summary.csv', index=False)
    return summary
