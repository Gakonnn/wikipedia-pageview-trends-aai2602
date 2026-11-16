"""Build the report from measured outputs, not hand-entered results."""
import json
import sys
from pathlib import Path
from xml.sax.saxutils import escape
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from wiki_trends.config import ROOT,RESULTS

import matplotlib
fontdir=Path(matplotlib.get_data_path())/'fonts/ttf'
# A portable report build can supply a directory containing DejaVuSans TTF files.
if len(sys.argv)>1: fontdir=Path(sys.argv[1])
for name,file in [('DV','DejaVuSans.ttf'),('DV-Bold','DejaVuSans-Bold.ttf')]:pdfmetrics.registerFont(TTFont(name,str(fontdir/file)))
pdfmetrics.registerFontFamily('DV',normal='DV',bold='DV-Bold',italic='DV',boldItalic='DV-Bold')
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='BodyRU',fontName='DV',fontSize=10.3,leading=15,spaceAfter=9,textColor=colors.HexColor('#243746')))
styles.add(ParagraphStyle(name='TitleRU',fontName='DV-Bold',fontSize=27,leading=34,spaceAfter=20,textColor=colors.HexColor('#102A43')))
styles.add(ParagraphStyle(name='H1RU',fontName='DV-Bold',fontSize=19,leading=25,spaceAfter=15,textColor=colors.HexColor('#102A43')))
styles.add(ParagraphStyle(name='SmallRU',fontName='DV',fontSize=8.2,leading=11,spaceAfter=7,textColor=colors.HexColor('#486581')))
styles.add(ParagraphStyle(name='Cell',fontName='DV',fontSize=8.4,leading=12))
flow=[]
def p(text,style='BodyRU'):flow.append(Paragraph(text,styles[style]))
def h(text):p(text,'H1RU')
def page():flow.append(PageBreak())
def fig(name,maxheight=340):
 im=Image(str(RESULTS/'figures'/name));ratio=min(495/im.imageWidth,maxheight/im.imageHeight);im.drawWidth=im.imageWidth*ratio;im.drawHeight=im.imageHeight*ratio;flow.append(im);flow.append(Spacer(1,8))
def table(headers,rows,widths=None):
 values=[[Paragraph(escape(str(v)),styles['Cell']) for v in row] for row in [headers]+rows]
 t=Table(values,colWidths=widths or [495/len(headers)]*len(headers),repeatRows=1,hAlign='LEFT')
 t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#DCEEF2')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),('LINEBELOW',(0,0),(-1,0),.7,colors.HexColor('#159B8E')),('LINEBELOW',(0,1),(-1,-1),.25,colors.HexColor('#D9E2EC'))]));flow.append(t);flow.append(Spacer(1,10))
audit=json.loads((RESULTS/'hourly_audit.json').read_text(encoding='utf-8'));daily=json.loads((RESULTS/'daily_audit.json').read_text(encoding='utf-8'));summary=json.loads((RESULTS/'analysis_summary.json').read_text(encoding='utf-8'))
from wiki_trends.forecast import METHODS
metrics=pd.read_csv(RESULTS/'forecast_metrics.csv');backtest=pd.read_csv(RESULTS/'forecast_backtest_summary.csv');insights=json.loads((RESULTS/'sql_insights.json').read_text(encoding='utf-8'));bench=pd.read_csv(RESULTS/'storage_benchmark.csv');selection=json.loads((RESULTS/'forecast_protocol.json').read_text(encoding='utf-8'))['selection']
fmt=lambda x:f'{x:,.0f}'.replace(',',' ')
p('Wikipedia<br/>Pageview Trends','TitleRU')
p('Итоговый проект по дисциплине<br/><b>Programming for Data Analysis and Database</b>')
p('Applied Artificial Intelligence · магистратура · AAI-2602')
flow.append(Spacer(1,18))
h('Исследовательский вопрос')
p('Как меняется число просмотров Wikipedia на казахском, русском и английском языках, какие из выбранных тем привлекают внимание и насколько хорошо простые методы предсказывают просмотры следующего дня?')
table(['Участник','Группа'],[['Tugelbayev Galymzhan','AAI-2602'],['Dias Ilyas','AAI-2602'],['Zhasulan Aidos','AAI-2602']],[340,155])
p(f'<b>Объём:</b> {fmt(audit["source_rows"])} строк просмотрено, {fmt(audit["selected_rows"])} строк сохранено для трёх языков. Дневной набор: {fmt(daily["rows"])} наблюдений за 2025 год.')
p('<b>Результат проекта:</b> воспроизводимый Python-процесс, нормализованная SQLite-база, пятнадцать SQL-запросов, EDA, сравнение пяти методов прогноза с проверкой на шести месячных фолдах, и форматов хранения, интерактивный Streamlit-дашборд.')
p('Дата подготовки: 16 ноября 2026 года. Тема 6. Распределение ответственности согласовано представителем команды. Статус внешней публикации и сдачи проверяется отдельно.','SmallRU')
page();h('1. Источники и единицы наблюдения')
table(['Набор','Охват','Назначение'],[
 ['Почасовой gzip','01.10.2025, 11:00-12:00 UTC','Большие данные, страницы, SQL, сравнение форматов'],
 ['Analytics API','01.01-31.12.2025, ежедневно','Динамика, сезонность, темы и прогноз'],
 ['Wikidata','6 сущностей, 3 языковых статьи','Сопоставление одной темы между языками']], [110,175,210])
p('Почасовой файл содержит агрегат для страницы и способа доступа. Время в имени файла обозначает конец часа. Отбираются только точные коды en/en.m, ru/ru.m, kk/kk.m. Другие проекты Wikimedia исключаются. Язык раздела не определяет страну посетителя.')
p('Дневные данные получены через API с параметрами all-access и user. Три ряда описывают весь языковой раздел, ещё 18 рядов - шесть отдельных тем. Почасовые и дневные данные хранятся раздельно и не суммируются между собой.')
p('Темы: Казахстан, Алматы, Астана, искусственный интеллект, Python и Интернет. Заголовки взяты из сохранённых Wikidata sitelinks. Статьи сопоставлены по сущности, а не переводом строки. Переименования и перенаправления могут ограничивать историческую полноту подсчёта.')
p('Для каждого исходного файла сохранены URL, дата получения, размер и SHA-256. Публичные аналитические данные Wikimedia распространяются по CC0. Точные ссылки приведены в manifest.json и списке источников.')
h('Качество и очистка')
p(f'Невалидных строк среди выбранных: {audit["invalid_selected"]}. Пропущенных дней: {len(daily["missing_dates"])}. Пропущенных ячеек дневного набора: {daily["missing_cells"]}. Проверки не допускают отрицательные просмотры и повторные ключи. Значение 0 сохраняется как реальное наблюдение; отсутствующая дата вызывает ошибку.')
p('IQR помечает необычные значения отдельно для каждого ряда. Помеченные наблюдения сохраняются: всплеск может отражать интерес к событию. Технически успешная загрузка сама по себе не доказывает отсутствие ошибок измерения у источника.')
page();h('2. Обработка и архитектура Python')
p('Поток работы: скачивание и проверка файлов; чтение gzip порциями; фильтрация и оптимизация типов; Parquet; нормализованная SQLite-база; SQL в Pandas; анализ и прогнозы; дашборд.')
table(['Модуль','Назначение'],[['acquire.py','HTTP, повторные попытки, кэш и контрольные суммы'],['prepare.py','Чанки, проверка данных, категории, Parquet'],['database.py + sql/','Нормализованная схема, ключи, пятнадцать запросов'],['analyze.py','Описательная статистика, IQR, STL и графики'],['forecast.py','Лаги, 5 методов, MAE/RMSE/MAPE/MASE, backtest, анализ ошибок'],['benchmark.py','Сравнение одинаковых агрегатов; замер памяти на Windows/macOS/Linux'],['main.py / app.py','Консольное меню / интерактивные фильтры']],[170,325])
p(f'Размер чанка ограничен {fmt(audit["max_chunk_rows"])} строками. Максимальный измеренный размер выбранного чанка до оптимизации: {audit["max_raw_chunk_bytes"]/1024**2:.2f} МиБ; после оптимизации: {audit["max_optimized_chunk_bytes"]/1024**2:.2f} МиБ. Это pandas memory_usage(deep=True), а не пик памяти всего процесса.')
p('Код использует более пяти функций, списки и словари, if/elif/else, циклы, чтение/запись файлов и try/except. При ошибке построения БД рабочая база сохраняется: сначала создаётся новый временный файл. Тесты проверяют отсутствие использования будущих значений, ключи базы и пересчёт метрик.')
p('requirements.txt фиксирует проверенные версии. main.py --all воспроизводит загрузку и расчёты. main.py --offline использует сохранённые источники. streamlit run app.py запускает интерфейс.')
page();h('3. База данных и SQL')
# Schema diagram is an evidence diagram with explicit keys and relations.
d=Drawing(495,285)
boxes={'languages':(0,220,145,55),'pages':(175,220,145,55),'hourly_views':(350,220,145,55),'project_daily':(0,105,145,65),'topic_pages':(175,105,145,65),'topic_daily':(350,105,145,65),'topics':(175,0,145,60)}
fields={'languages':'PK language','pages':'PK page_id / FK language','hourly_views':'PK page_id, hour_end, access','project_daily':'PK language, date','topic_pages':'PK topic_id, language\nFK page_id','topic_daily':'PK topic_id, language, date','topics':'PK topic_id / category'}
for x1,y1,x2,y2 in [(145,247,175,247),(320,247,350,247),(72,220,72,170),(247,220,247,170),(320,137,350,137),(247,60,247,105)]:d.add(Line(x1,y1,x2,y2,strokeColor=colors.HexColor('#159B8E'),strokeWidth=1.5))
for name,(x,y,w,ht) in boxes.items():
 d.add(Rect(x,y,w,ht,fillColor=colors.HexColor('#EEF5F7'),strokeColor=colors.HexColor('#A8C8D0')));d.add(String(x+7,y+ht-18,name,fontName='DV-Bold',fontSize=9))
 for k,line in enumerate(fields[name].split('\n')):d.add(String(x+7,y+ht-33-k*11,line,fontName='DV',fontSize=6.7))
flow.append(d);flow.append(Spacer(1,12))
p('Связи имеют вид 1:N. Составной внешний ключ topic_daily(topic_id, language) ссылается на topic_pages. Дополнительно topic_pages.language ссылается на languages. Полная схема с типами, ограничениями и индексами находится в sql/schema.sql; ER в Mermaid - docs/ER_diagram.md.','SmallRU')
table(['Запросы','Что проверяют или показывают'],[['01-02','Просмотры по языку/доступу; топ-10 страниц в каждом языке (JOIN, CTE, ROW_NUMBER)'],['03-04','Месячные суммы; популярность тем (GROUP BY, HAVING)'],['05-06','Среднее за 7 дней; изменение к предыдущему дню (AVG OVER, LAG)'],['07-08','Дни выше среднего (подзапрос); доля темы на миллион просмотров (JOIN)'],['09-10','Дни недели; сопоставление статей по Wikidata'],['11-12','Ранг тем по месяцам (CTE, RANK); эффект выходных (CASE, условная агрегация)'],['13','Три пиковых дня каждой темы относительно среднего (AVG OVER, DENSE_RANK)'],['14-15','Накопленная доля годовых просмотров (SUM OVER); доля темы между языками (CTE, HAVING-подзапрос, окно)']],[90,405])
p('Все пятнадцать запросов выполняются, результаты загружаются через pd.read_sql_query и сохраняются в results/sql. Дашборд позволяет просмотреть текст запроса и таблицу результата. Результаты запросов 11, 12, 14 и 15 используются в анализе (рисунок ниже, results/sql_insights.json).')
fig('08_sql_insights.png',190)
wk=insights['weekend_to_weekday'];hy=insights['half_year_pct']
p('Выходные/будни: '+', '.join(f'{l}: {wk[l]:.3f}' for l in ['en','ru','kk'])+'. Значение ниже 1 означает, что в выходные просмотров меньше. Доля годовых просмотров к 30 июня: '+', '.join(f'{l}: {hy[l]:.1f}%' for l in ['en','ru','kk'])+'. Наибольший относительный интерес к теме (на миллион просмотров раздела): '+'; '.join(f'{t} - {l}' for t,l in insights['highest_relative_interest'].items())+'.')
page();h('4. Динамика, распределение и корреляция')
fig('01_daily_trends.png',345)
table(['Язык','Просмотры за 2025 год','В среднем за день'],[[l,fmt(summary['annual_views'][l]),fmt(summary['mean_daily'][l])] for l in ['en','ru','kk']],[85,205,205])
p('Масштабы языковых разделов существенно различаются, поэтому линии показаны на отдельных осях. Скользящее среднее сглаживает дневные колебания. Месячные суммы получены resample и зависят также от числа дней в месяце.')
corr=pd.read_csv(RESULTS/'correlation_levels.csv',index_col=0)
p(f'Корреляции дневных уровней: en-ru {corr.loc["en","ru"]:.3f}, en-kk {corr.loc["en","kk"]:.3f}, ru-kk {corr.loc["ru","kk"]:.3f}. Это описательная связь; общие тренды и недельная сезонность могут её усиливать. Корреляции дневных изменений сохранены отдельно.')
page();h('5. Выбросы и выбранные темы')
fig('02_boxplots.png',220)
iqr=pd.read_csv(RESULTS/'iqr_audit.csv');q=iqr[iqr.topic_id.eq('__total__')]
p('Дни вне границ IQR для полных разделов: '+', '.join(f'{r.language}: {r.flagged}' for r in q.itertuples())+'. Эти дни остаются в расчётах. Boxplot показывает асимметрию распределения и необычные наблюдения.')
fig('05_topic_totals.png',245)
p('Лидер среди шести выбранных тем по каждому языку: '+ '; '.join(f'{r["language"]}: {r["topic"]} ({fmt(r["views"])} просмотров)' for r in summary['top_topics'])+'.')
p('Это рейтинг только выбранного набора тем. Относительный интерес сравнивается в дашборде через просмотры темы на миллион просмотров раздела. Ни абсолютные значения, ни такая доля не являются числом уникальных читателей.','SmallRU')
page();h('6. Недельная сезонность')
fig('04_stl.png',445)
p('Для казахской Wikipedia применена робастная STL-декомпозиция к log1p(просмотры) с периодом 7 дней. Компоненты: наблюдаемый ряд, плавный тренд, повторяющаяся недельная часть и остаток. Логарифм уменьшает влияние масштаба всплесков.')
p('Период 7 выбран заранее по календарной неделе. Один год даёт много недельных циклов, но недостаточен для надёжной оценки многолетней сезонности. STL используется только для описания ряда. Его компоненты не подаются в прогноз, потому что разложение полного года использует и будущие точки.')
page();h('7. Прогноз без использования будущего')
p('Цель: просмотры всего языкового раздела на следующий день. Обучение - январь-сентябрь, validation - октябрь-ноябрь (61 день), test - декабрь (31 день). Первые 28 дней служат историей для лагов. Разделение хронологическое, без shuffle.')
table(['Метод','Правило'],[['naive','Повторить вчерашнее значение, основной baseline'],['seasonal_naive','Повторить значение того же дня прошлой недели'],['moving_average_7','Среднее семи завершённых дней'],['linear_regression','Лаги 1/7/14/28, прошлые средние 7/28, день недели'],['gradient_boosting','HistGradientBoosting: отношение завтрашнего дня к среднему 7 дней по относительным лагам и дню недели']],[160,335])
p('Метод выбирается отдельно для каждого языка по наименьшему validation MAE. Для декабрьского теста регрессия переобучается на январе-ноябре. При переходе к следующему дню доступен фактический предыдущий день; это последовательный прогноз на один день вперёд. Все методы получают одинаковые даты оценки.')
rows=[]
for l in ['en','ru','kk']:
 for method in METHODS:
  v=metrics[(metrics.language==l)&(metrics.method==method)&(metrics.split=='validation')].iloc[0];t=metrics[(metrics.language==l)&(metrics.method==method)&(metrics.split=='test')].iloc[0]
  rows.append([l,method+(' *' if selection[l]==method else ''),fmt(v.mae),fmt(t.mae),f'{t.mase:.2f}',f'{t.mape:.1f}'])
table(['Язык','Метод','Val MAE','Test MAE','Test MASE','Test MAPE, %'],rows,[40,155,80,80,70,70])
p('* Метод выбран по validation. MASE делит MAE на средний модуль недельной разности на обучающих данных: значение меньше 1 лучше недельного naive. MAE измеряется в просмотрах/день. Малый MAE у менее посещаемого языка не означает лучшую модель относительно другого языка.','SmallRU')
page();h('8. Результат прогноза и ограничения')
fig('06_forecasts.png',360)
for l in ['en','ru','kk']:
 selected=metrics[(metrics.language==l)&(metrics.method==selection[l])&(metrics.split=='test')].iloc[0]
 base=metrics[(metrics.language==l)&(metrics.method=='naive')&(metrics.split=='test')].iloc[0]
 change=(base.mae-selected.mae)/base.mae*100
 p(f'<b>{l.upper()}:</b> выбран {selection[l]}, test MAE {fmt(selected.mae)}. Изменение MAE относительно naive: {change:+.1f}% улучшения (отрицательное значение означало бы ухудшение).')
p('Подбор по validation не гарантирует победу на test. Всплески интереса трудно предсказать по прошлым просмотрам. Поэтому дополнительно выполнен rolling-origin backtest: шесть месячных фолдов (июль-декабрь), для каждого месяца модели обучаются только на предыдущих днях. Backtest не используется для выбора модели, он проверяет устойчивость.')
page();h('8a. Устойчивость прогноза: шесть фолдов')
fig('09_backtest.png',200)
bt=backtest.sort_values(['language','mean_mae'])
table(['Язык','Метод','Средний MAE','Std MAE','Средний MASE','Средний ранг','Побед'],[[r.language,r.method,fmt(r.mean_mae),fmt(r.std_mae),f'{r.mean_mase:.2f}',f'{r.mean_rank:.1f}',r.wins] for r in bt.itertuples()],[40,125,75,70,65,65,55])
p('Анализ ошибок выбранного метода по дням недели на тесте сохранён в results/forecast_errors_by_weekday.csv и показан в дашборде.','SmallRU')
p('Время и пиковые выделения Python-памяти каждого прогноза записаны в forecast_metrics.csv. tracemalloc не охватывает всю нативную память библиотек. Поскольку ряды короткие, эти значения не следует обобщать на большие промышленные системы.')
page();h('9. Сравнение CSV, Parquet и SQLite')
p('В каждом варианте суммируются одни и те же почасовые просмотры по языку и типу доступа. CSV/Pandas читает всю таблицу в память (baseline); Parquet/Pandas читает порциями; SQLite выполняет JOIN и GROUP BY. Все итоговые суммы совпали точно.')
table(['Метод','Время, с','Пик RSS, МиБ','Файл, МиБ'],[[r.method,f'{r.seconds:.3f}',f'{r.peak_rss_mib:.1f}',f'{r.file_mib:.1f}'] for r in bench.itertuples()],[165,100,115,115])
p('Таблица показывает медианы трёх отдельных процессов на метод. Время включает чтение и агрегацию, но исключает запуск Python и импорт библиотек. RSS включает интерпретатор, импорты и нативные выделения. Кэш операционной системы не сбрасывался; результаты зависят от компьютера и порядка запуска.')
p('Размер SQLite включает нормализованные таблицы, индексы и дневные данные, поэтому это не сравнение только кодеков сжатия. Время построения базы не входит в скорость одного запроса. Точные повторения и протокол сохранены рядом с таблицей.')
best=bench.sort_values('seconds').iloc[0];small=bench.sort_values('peak_rss_mib').iloc[0]
p(f'В этом измерении самый быстрый вариант: <b>{best.method}</b>; минимальный пик RSS: <b>{small.method}</b>. Parquet выбран для компактного хранения и обработки по частям, SQLite - для связей, ограничений целостности и SQL, CSV - для совместимого экспорта.')
h('Интерфейс и демонстрация')
p('Streamlit включает выбор языка, года, периода и категории, графики тем, нормирование на размер раздела, поиск страниц часового среза, интерактивное сравнение прогнозов с выбором методов и backtest, пятнадцать SQL-запросов и аудит качества. Периодические фильтры относятся к дневным рядам; фиксированные эксперименты и SQL имеют явные подписи.')
page();h('10. Выводы, команда и воспроизводимость')
p(f'Проект обработал {fmt(audit["source_rows"])} исходных записей и сохранил {fmt(audit["selected_rows"])} наблюдений трёх языков. Объём превышает рекомендуемые 500 тысяч строк. Годовые API-ряды дополняют часовой срез и позволяют анализировать недели и месяцы без загрузки тысяч архивов.')
p('Проверены различия масштабов трафика, распределения просмотров и выбранных тем. Прогнозы оценены на одинаковых датах с отложенным тестом. Сравнение хранения показывает компромисс между удобством запросов, скоростью, размером и памятью. Ни один метод не объявляется универсально лучшим.')
table(['Участник, AAI-2602','Согласованная ответственность'],[['Tugelbayev Galymzhan','Источники, обработка, Python, воспроизводимость'],['Dias Ilyas','SQLite, ER-диаграмма, SQL (запросы 11-15 и SQL-анализ), расширение прогноза (gradient boosting, MASE/RMSE/MAPE, backtest, анализ ошибок), запуск и замер памяти на Windows, интерактивный прогноз в дашборде, тесты расширений'],['Zhasulan Aidos','EDA, прогнозы, визуализации и дашборд'],['Вся команда','Проверка выводов, отчёт, презентация, защита']],[190,305])
p('Роли согласованы как план работы и подготовки к защите. Перед сдачей команда должна подтвердить фактически выполненный вклад. Начальная реализация и материалы подготовлены с помощью AI; самостоятельная проверка и понимание каждого раздела остаются ответственностью участников.','SmallRU')
p('<b>Ограничения:</b> один час для анализа всех страниц; шесть выбранных тем; один год и один тестовый месяц; возможные изменения названий статей и фильтрации ботов; язык не равен географии; просмотры не равны уникальным пользователям.')
p('<b>Воспроизведение:</b> установить зависимости из requirements.txt, выполнить python main.py --all, затем python -m streamlit run app.py. Для проверки: python -m unittest discover -s tests -v. Полный архив содержит исходные ответы API и готовые результаты.')
h('Основные источники')
for title,url in [('Wikimedia: архив и лицензия','https://dumps.wikimedia.org/other/pageviews/readme.html'),('Формат почасового набора','https://wikitech.wikimedia.org/wiki/Data_Platform/Data_Lake/Traffic/Pageviews'),('Analytics API','https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/'),('Wikidata','https://www.wikidata.org/wiki/Wikidata:Data_access')]:
 p(f'<link href="{url}" color="#087F8C">{escape(title)}</link>','SmallRU')
p('Полный список технических источников: docs/SOURCES.md. URL каждого скачанного файла и SHA-256: data/raw/manifest.json. GitHub, регистрация темы и Moodle требуют отдельного подтверждения публикации.','SmallRU')

def footer(c,doc):
 c.setStrokeColor(colors.HexColor('#D9E2EC'));c.line(50,42,545,42);c.setFont('DV',8);c.setFillColor(colors.HexColor('#627D98'));c.drawString(50,29,'Wikipedia Pageview Trends · AAI-2602');c.drawRightString(545,29,str(doc.page))
out=ROOT/'output/pdf/Final_Project_Wikipedia_Trends_AAI-2602_Report.pdf';out.parent.mkdir(parents=True,exist_ok=True)
SimpleDocTemplate(str(out),pagesize=A4,rightMargin=50,leftMargin=50,topMargin=44,bottomMargin=56,title='Wikipedia Pageview Trends - AAI-2602',author='Tugelbayev Galymzhan; Dias Ilyas; Zhasulan Aidos').build(flow,onFirstPage=footer,onLaterPages=footer)
print(out)
