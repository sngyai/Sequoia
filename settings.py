# -*- encoding: UTF-8 -*-


def init():
    global DB_DIR, DATA_DIR, NOTIFY, CONFIG, STOCKS_FILE
    DATA_DIR = 'data'
    DB_DIR = 'storage'
    NOTIFY = True
    STOCKS_FILE = './storage/stocks.csv'
    # CONFIG = 'config/主板200亿-创业板100亿.xlsx'
    # CONFIG = 'config/沪深A股.xlsx'
