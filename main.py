"""Run from the project folder: python main.py --all or python main.py."""
import argparse
import json
import sqlite3
from wiki_trends.config import ensure_directories, RESULTS

def prepare():
    from wiki_trends.prepare import prepare_hourly, prepare_daily
    from wiki_trends.database import build_database, run_queries
    print(prepare_hourly(),flush=True)
    print('Daily rows:',len(prepare_daily()),flush=True)
    print('Database:',build_database(),flush=True)
    print('SQL:',run_queries(),flush=True)

def analyze():
    from wiki_trends.analyze import analyze_data,plot_forecasts
    from wiki_trends.forecast import compare_forecasts
    analyze_data()
    print(compare_forecasts().to_string(index=False),flush=True)
    plot_forecasts()

def menu():
    from wiki_trends.acquire import download_data
    from wiki_trends.database import run_queries
    from wiki_trends.benchmark import benchmark
    actions={'1':download_data,'2':prepare,'3':analyze,'4':run_queries,'5':benchmark}
    while True:
        print('\n1 - Скачать данные\n2 - Очистить и построить БД\n3 - Анализ и прогнозы\n4 - SQL-запросы\n5 - Сравнение форматов\n0 - Выход')
        choice=input('Выберите действие: ').strip()
        if choice=='0': break
        elif choice in actions:
            try: print(actions[choice]())
            except (OSError,ValueError,sqlite3.Error) as error: print('Ошибка:',error)
        else: print('Введите число из меню.')

def main():
    parser=argparse.ArgumentParser(description='Wikipedia Pageview Trends')
    parser.add_argument('--all',action='store_true',help='Download and rebuild all results')
    parser.add_argument('--offline',action='store_true',help='Rebuild from cached raw sources')
    args=parser.parse_args();ensure_directories()
    if args.all or args.offline:
        if not args.offline:
            from wiki_trends.acquire import download_data
            download_data()
        prepare();analyze()
        from wiki_trends.benchmark import benchmark
        print(benchmark().to_string(index=False))
        print('Готово:',RESULTS)
    else: menu()

if __name__=='__main__': main()
