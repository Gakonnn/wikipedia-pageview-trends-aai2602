"""One-day-ahead evaluation. Features only use observations before the target day."""
import json
import tracemalloc
from time import perf_counter
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error
from .config import PROCESSED, RESULTS

def lag_features(series):
    frame = pd.DataFrame({'y':series})
    for lag in [1,7,14,28]:
        frame[f'lag_{lag}'] = series.shift(lag)
    frame['ma7'] = series.shift(1).rolling(7).mean()
    frame['ma28'] = series.shift(1).rolling(28).mean()
    frame['dow_sin'] = np.sin(2*np.pi*frame.index.dayofweek/7)
    frame['dow_cos'] = np.cos(2*np.pi*frame.index.dayofweek/7)
    return frame.dropna()

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
    raise ValueError(f'Unknown method {method}')

def compare_forecasts():
    daily = pd.read_parquet(PROCESSED / 'daily.parquet')
    metrics, predictions, selections = [], [], {}
    for lang,g in daily[daily.topic_id.eq('__total__')].groupby('language'):
        series = g.set_index('date')['views'].sort_index().asfreq('D')
        if series.isna().any():
            raise ValueError('Forecast requires complete daily data')
        frame = lag_features(series)
        for split in ['validation','test']:
            boundary = '2025-10-01' if split == 'validation' else '2025-12-01'
            finish = '2025-12-01' if split == 'validation' else '2026-01-01'
            training = frame.index < boundary
            evaluation = (frame.index >= boundary) & (frame.index < finish)
            for method in ['naive','seasonal_naive','moving_average_7','linear_regression']:
                tracemalloc.start()
                start = perf_counter()
                pred = predict_method(method,frame,training,evaluation)
                seconds = perf_counter()-start
                _,peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                actual = frame.loc[evaluation,'y'].to_numpy()
                metrics.append(dict(language=lang,split=split,method=method,n=len(actual),
                    mae=mean_absolute_error(actual,pred),seconds=seconds,python_peak_kib=peak/1024))
                for date,a,p in zip(frame.index[evaluation],actual,pred):
                    predictions.append(dict(language=lang,split=split,method=method,date=date,actual=a,predicted=p))
        val = pd.DataFrame(metrics).query('language == @lang and split == "validation"')
        selections[lang] = val.sort_values(['mae','method']).iloc[0]['method']
    metrics = pd.DataFrame(metrics)
    metrics['selected_on_validation'] = metrics.apply(lambda r: selections[r.language]==r.method,axis=1)
    metrics.to_csv(RESULTS / 'forecast_metrics.csv',index=False)
    pd.DataFrame(predictions).to_csv(RESULTS / 'forecast_predictions.csv',index=False)
    (RESULTS / 'forecast_protocol.json').write_text(json.dumps(dict(
        train='2025-01-01..2025-09-30 (first 28 days warm-up)',validation='2025-10-01..2025-11-30',
        test='2025-12-01..2025-12-31', horizon='rolling one day ahead; past actual observations available',
        refit='linear model fitted on train for validation, train+validation for test',
        metric='MAE in views/day, compare methods within each language',
        memory='tracemalloc peak Python allocations; excludes most native-library memory',
        selection=selections),indent=2))
    return metrics
