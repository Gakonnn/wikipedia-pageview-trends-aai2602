import json
import sqlite3
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import plotly.express as px
from statsmodels.tsa.seasonal import STL
from .config import PROCESSED, RESULTS, DB

COLORS = {'en':'#2878B5','ru':'#D97929','kk':'#159B8E'}

def save_figure(fig, name):
    fig.savefig(RESULTS / 'figures' / f'{name}.png',dpi=170,bbox_inches='tight')
    plt.close(fig)

def analyze_data():
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    df = pd.read_parquet(PROCESSED / 'daily.parquet')
    totals = df[df.topic_id.eq('__total__')].pivot(index='date',columns='language',values='views').sort_index()
    totals.describe().T.to_csv(RESULTS / 'daily_descriptive.csv')
    pd.DataFrame({'column':df.columns,'dtype':df.dtypes.astype(str).values,
                  'missing':df.isna().sum().values}).to_csv(RESULTS / 'daily_schema.csv',index=False)
    audits = []
    for (lang,topic),g in df.groupby(['language','topic_id']):
        q1,q3 = g.views.quantile([.25,.75])
        low,high = max(0,q1-1.5*(q3-q1)),q3+1.5*(q3-q1)
        flags = (g.views<low)|(g.views>high)
        audits.append(dict(language=lang,topic_id=topic,q1=q1,q3=q3,lower=low,upper=high,
                           flagged=int(flags.sum()),zeros=int(g.views.eq(0).sum())))
    pd.DataFrame(audits).to_csv(RESULTS / 'iqr_audit.csv',index=False)
    # Spikes are observations of interest. IQR flags do not delete data.
    monthly = totals.resample('MS').sum()
    monthly.to_csv(RESULTS / 'monthly_views.csv')
    fig,axes=plt.subplots(3,1,figsize=(11,8),sharex=True)
    for ax,lang in zip(axes,['en','ru','kk']):
        ax.plot(totals.index,totals[lang],color=COLORS[lang],alpha=.35,label='Daily')
        ax.plot(totals.index,totals[lang].rolling(7).mean(),color=COLORS[lang],label='7-day mean')
        ax.set_ylabel(f'{lang.upper()} views/day');ax.legend(loc='upper right');ax.ticklabel_format(axis='y',style='sci',scilimits=(0,0))
    fig.suptitle('Wikipedia project pageviews, 2025 (user, all-access, UTC)')
    fig.tight_layout();save_figure(fig,'01_daily_trends')
    interactive=px.line(df[df.topic_id.eq('__total__')],x='date',y='views',color='language',facet_row='language',
                        title='Daily Wikipedia views, 2025',color_discrete_map=COLORS)
    interactive.update_yaxes(matches=None)
    interactive.write_html(RESULTS / 'figures/interactive_trends.html',include_plotlyjs=True)
    fig,axes=plt.subplots(1,3,figsize=(11,4))
    for ax,lang in zip(axes,['en','ru','kk']):
        ax.boxplot(totals[lang],tick_labels=[lang.upper()]);ax.set_ylabel('Daily views');ax.ticklabel_format(axis='y',style='sci',scilimits=(0,0))
    fig.suptitle('Daily view distribution; outliers retained');fig.tight_layout();save_figure(fig,'02_boxplots')
    corr=totals.corr();corr.to_csv(RESULTS / 'correlation_levels.csv')
    totals.pct_change().dropna().corr().to_csv(RESULTS / 'correlation_changes.csv')
    fig,ax=plt.subplots(figsize=(6,5));im=ax.imshow(corr,vmin=-1,vmax=1,cmap='RdBu_r')
    ax.set_xticks(range(3),corr.columns);ax.set_yticks(range(3),corr.index)
    for i in range(3):
        for j in range(3): ax.text(j,i,f'{corr.iloc[i,j]:.2f}',ha='center',va='center',color='white' if abs(corr.iloc[i,j])>.6 else 'black')
    fig.colorbar(im,ax=ax,label='Pearson r');ax.set_title('Correlation of daily project views');save_figure(fig,'03_correlation')
    # Weekly seasonality: a one-year sample supports many seven-day cycles.
    stl=STL(np.log1p(totals['kk']),period=7,robust=True).fit()
    components=pd.DataFrame({'observed_log1p':np.log1p(totals.kk),'trend':stl.trend,'weekly':stl.seasonal,'residual':stl.resid})
    components.to_csv(RESULTS / 'stl_kk.csv')
    fig,axes=plt.subplots(4,1,figsize=(11,8),sharex=True)
    for ax,col in zip(axes,components): ax.plot(components.index,components[col],color=COLORS['kk']);ax.set_ylabel(col)
    fig.suptitle('Kazakh Wikipedia: robust STL, weekly period = 7, log1p scale');fig.tight_layout();save_figure(fig,'04_stl')
    with sqlite3.connect(DB) as con:
        topic=pd.read_sql_query('SELECT t.name topic,d.language,SUM(d.views) views FROM topic_daily d JOIN topics t USING(topic_id) GROUP BY d.topic_id,d.language',con)
        hour=pd.read_sql_query('SELECT p.language,h.access,COUNT(*) records,SUM(h.views) views FROM hourly_views h JOIN pages p USING(page_id) GROUP BY p.language,h.access',con)
    topic.to_csv(RESULTS / 'topic_totals.csv',index=False)
    fig,axes=plt.subplots(1,3,figsize=(13,5))
    for ax,lang in zip(axes,['en','ru','kk']):
        g=topic[topic.language.eq(lang)].sort_values('views')
        ax.barh(g.topic,g.views,color=COLORS[lang]);ax.set_title(lang.upper());ax.set_xlabel('Views in 2025')
    fig.tight_layout();save_figure(fig,'05_topic_totals')
    hourly_summary=hour.to_dict('records')
    (RESULTS / 'analysis_summary.json').write_text(json.dumps(dict(
        annual_views={k:int(v) for k,v in totals.sum().items()},
        mean_daily={k:float(v) for k,v in totals.mean().items()},
        hourly=hourly_summary, top_topics=topic.sort_values('views',ascending=False).groupby('language').first().reset_index().to_dict('records'),
        interpretation='IQR flags retained; correlation is descriptive, not causal; language is not country'),indent=2))

def plot_forecasts():
    metrics=pd.read_csv(RESULTS / 'forecast_metrics.csv')
    pred=pd.read_csv(RESULTS / 'forecast_predictions.csv',parse_dates=['date'])
    selected=json.loads((RESULTS / 'forecast_protocol.json').read_text())['selection']
    fig,axes=plt.subplots(3,1,figsize=(11,8),sharex=True)
    for ax,lang in zip(axes,['en','ru','kk']):
        g=pred[(pred.language==lang)&(pred.split=='test')&(pred.method==selected[lang])]
        ax.plot(g.date,g.actual,color=COLORS[lang],label='Actual')
        ax.plot(g.date,g.predicted,color='#323F4B',linestyle='--',label=selected[lang])
        ax.set_ylabel(f'{lang.upper()} views');ax.legend()
    fig.suptitle('December test: rolling one-day forecasts, model selected on Oct-Nov');fig.tight_layout();save_figure(fig,'06_forecasts')
    fig,axes=plt.subplots(1,3,figsize=(12,4))
    for ax,lang in zip(axes,['en','ru','kk']):
        g=metrics[(metrics.language==lang)&(metrics.split=='test')]
        ax.bar(g.method,g.mae,color=COLORS[lang]);ax.tick_params(axis='x',labelrotation=65);ax.set_title(lang.upper());ax.set_ylabel('Test MAE, views/day')
    fig.tight_layout();save_figure(fig,'07_mae')
