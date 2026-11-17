"""Interactive local dashboard: streamlit run app.py"""
import json
import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st
from wiki_trends.config import DB, PROCESSED, RESULTS
from wiki_trends.database import load_queries

st.set_page_config(page_title='Wikipedia Trends',page_icon='🌐',layout='wide')
st.title('Wikipedia Pageview Trends')
st.caption('AAI-2602 · Tugelbayev Galymzhan · Dias Ilyas · Zhasulan Aidos')
if not DB.exists():
    st.error('Данные ещё не подготовлены. Запустите: python main.py --all')
    st.stop()

@st.cache_data
def read_daily(file_version):
    return pd.read_parquet(PROCESSED/'daily.parquet')

df=read_daily((PROCESSED/'daily.parquet').stat().st_mtime_ns)
st.sidebar.header('Фильтры')
languages=st.sidebar.multiselect('Языки',['kk','ru','en'],default=['kk','ru','en'])
year=st.sidebar.selectbox('Год',sorted(df.date.dt.year.unique()))
category=st.sidebar.selectbox('Категория',['Все темы']+sorted(x for x in df.category.unique() if x!='All pages'))
date_range=st.sidebar.date_input('Период',(df.date.min().date(),df.date.max().date()),
                                 min_value=df.date.min().date(),max_value=df.date.max().date())
st.sidebar.caption('Язык Wikipedia не означает страну посетителя. Данные за 2025 год, время UTC.')
if not languages or len(date_range)!=2:
    st.info('Выберите язык и обе границы периода.');st.stop()
filtered=df[df.language.isin(languages)&df.date.dt.year.eq(year)&
            df.date.between(pd.Timestamp(date_range[0]),pd.Timestamp(date_range[1]))]
tabs=st.tabs(['Тренды','Темы','Почасовой срез','Прогнозы','SQL','Качество данных'])
with tabs[0]:
    totals=filtered[filtered.topic_id.eq('__total__')].copy()
    st.metric('Просмотры выбранных языковых разделов',f'{totals.views.sum():,}')
    st.caption('Все страницы языкового раздела, все способы доступа, категория agent=user.')
    normalize=st.checkbox('Индекс: первый день периода = 100',value=True)
    totals['value']=totals.groupby('language').views.transform(lambda x:x/x.iloc[0]*100) if normalize else totals.views
    fig=px.line(totals,x='date',y='value',color='language',labels={'value':'Индекс' if normalize else 'Просмотры','date':'Дата','language':'Язык'})
    st.plotly_chart(fig,width='stretch')
    monthly=totals.groupby(['language',pd.Grouper(key='date',freq='MS')]).views.sum().reset_index()
    st.plotly_chart(px.bar(monthly,x='date',y='views',color='language',barmode='group',title='Суммы по месяцам внутри выбранного периода'),width='stretch')
with tabs[1]:
    topics=filtered[filtered.topic_id.ne('__total__')].copy()
    if category!='Все темы':topics=topics[topics.category.eq(category)]
    topic=st.selectbox('Тема',sorted(topics.topic.unique())) if len(topics) else None
    if topic:
        data=topics[topics.topic.eq(topic)].merge(filtered[filtered.topic_id.eq('__total__')][['date','language','views']],on=['date','language'],suffixes=('','_total'))
        data['views_per_million']=data.views/data.views_total*1_000_000
        relative=st.checkbox('На миллион просмотров раздела',value=True)
        st.plotly_chart(px.line(data,x='date',y='views_per_million' if relative else 'views',color='language',title=topic),width='stretch')
        st.caption('Сопоставление статей по Wikidata. Учитываются указанные заголовки; перенаправления и переименования ограничивают полноту.')
        st.download_button('Скачать выбранные данные CSV',data.to_csv(index=False).encode('utf-8-sig'),'topic_views.csv','text/csv')
with tabs[2]:
    st.subheader('1 октября 2025, 11:00–12:00 UTC')
    st.caption('Отдельный полный часовой срез. Фильтры даты, года и категории относятся к дневным рядам.')
    query=st.text_input('Название страницы содержит')
    lang=st.selectbox('Язык почасового среза',languages)
    with sqlite3.connect(DB) as con:
        page_data=pd.read_sql_query('SELECT p.title,SUM(h.views) views FROM hourly_views h JOIN pages p USING(page_id) '
            'WHERE p.language=? AND instr(lower(p.title),lower(?))>0 GROUP BY p.page_id ORDER BY views DESC LIMIT 100',con,params=(lang,query))
    st.dataframe(page_data,width='stretch',hide_index=True)
with tabs[3]:
    st.caption('Фиксированный эксперимент: обучение январь–сентябрь, validation октябрь–ноябрь, test декабрь. Фильтры периода и категории не меняют протокол.')
    metrics=pd.read_csv(RESULTS/'forecast_metrics.csv')
    predictions=pd.read_csv(RESULTS/'forecast_predictions.csv',parse_dates=['date'])
    selection=json.loads((RESULTS/'forecast_protocol.json').read_text(encoding='utf-8'))['selection']
    columns=st.columns(3)
    forecast_lang=columns[0].selectbox('Язык прогноза',languages)
    split=columns[1].radio('Выборка',['test','validation'],horizontal=True)
    all_methods=list(metrics.method.unique())
    chosen=columns[2].multiselect('Методы',all_methods,default=sorted({'naive',selection[forecast_lang]}))
    shown=predictions[(predictions.language==forecast_lang)&(predictions.split==split)&predictions.method.isin(chosen)]
    actual=shown.drop_duplicates('date')[['date','actual']].rename(columns={'actual':'value'}).assign(series='actual')
    lines=pd.concat([actual,shown.rename(columns={'predicted':'value','method':'series'})[['date','value','series']]])
    st.plotly_chart(px.line(lines,x='date',y='value',color='series',markers=True,
        labels={'value':'Просмотры/день','date':'Дата','series':'Ряд'},
        title=f'{forecast_lang.upper()}: прогноз на день вперёд ({split}); выбран по validation: {selection[forecast_lang]}'),width='stretch')
    
    if not shown.empty:
        residuals = shown.copy()
        residuals["error"] = residuals["actual"] - residuals["predicted"]

        fig_errors = px.bar(
            residuals,
            x="date",
            y="error",
            color="method",
            barmode="group",
            title="Ошибки прогнозирования по датам",
            labels={
                "date": "Дата",
                "error": "Фактические − предсказанные просмотры",
                "method": "Модель"
            }
        )

        fig_errors.add_hline(y=0, line_dash="dash")

        st.plotly_chart(fig_errors, width="stretch")

        st.caption(
            "Положительная ошибка означает, что модель "
            "недооценила просмотры. Отрицательная — переоценила."
        )

        st.download_button(
            "Скачать ошибки прогнозирования",
            residuals.to_csv(index=False).encode("utf-8-sig"),
            "forecast_residuals.csv",
            "text/csv"
        )

    table=metrics[(metrics.language==forecast_lang)&(metrics.split==split)][['method','mae','rmse','mape','mase','seconds','selected_on_validation']]
    st.dataframe(table.sort_values('mae'),width='stretch',hide_index=True)
    st.info('Каждый прогноз на один день вперёд использует известные предыдущие дни. Это не прогноз всего декабря из одной точки. MASE < 1 означает лучше, чем недельный naive на обучающих данных.')
    if (RESULTS/'forecast_backtest_summary.csv').exists():
        st.subheader('Проверка устойчивости: 6 месячных фолдов (июль–декабрь)')
        backtest=pd.read_csv(RESULTS/'forecast_backtest.csv')
        st.plotly_chart(px.line(backtest[backtest.language==forecast_lang],x='fold',y='mase',color='method',markers=True,
            labels={'fold':'Месяц','mase':'MASE','method':'Метод'}),width='stretch')
        summary=pd.read_csv(RESULTS/'forecast_backtest_summary.csv')
        st.dataframe(summary[summary.language==forecast_lang].sort_values('mean_mae'),width='stretch',hide_index=True)
    if (RESULTS/'forecast_errors_by_weekday.csv').exists():
        errors=pd.read_csv(RESULTS/'forecast_errors_by_weekday.csv')
        st.caption('Анализ ошибок выбранного метода на test по дням недели')
        st.dataframe(errors[errors.language==forecast_lang],width='stretch',hide_index=True)
with tabs[4]:
    queries=load_queries();name=st.selectbox('Сохранённый SQL-запрос',list(queries))
    st.code(queries[name],language='sql')
    with sqlite3.connect(DB) as con: result=pd.read_sql_query(queries[name],con)
    st.dataframe(result,width='stretch',hide_index=True)
    st.caption('SQL-запросы работают по всей базе, независимо от фильтров боковой панели.')
with tabs[5]:
    st.json(json.loads((RESULTS/'hourly_audit.json').read_text(encoding='utf-8')))
    st.json(json.loads((RESULTS/'daily_audit.json').read_text(encoding='utf-8')))
    st.dataframe(pd.read_csv(RESULTS/'iqr_audit.csv'),hide_index=True)
    st.caption('Выбросы IQR сохранены: всплеск просмотров может быть реальным событием. Пропущенный день не заменяется нулём.')
