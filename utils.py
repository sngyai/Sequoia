# -*- coding: UTF-8 -*-
import datetime

import xlrd
import pandas as pd
import os
import time

DATA_DIR = 'data'
ONE_HOUR_SECONDS = 60 * 60


# 获取股票代码列表
def get_stocks(config=None):
    if config:
        data = xlrd.open_workbook(config)
        table = data.sheets()[0]
        rows_count = table.nrows
        codes = table.col_values(0)[1:rows_count-1]
        names = table.col_values(1)[1:rows_count-1]
        return list(zip(codes, names))
    else:
        data_files = os.listdir(DATA_DIR)
        stocks = []
        for file in data_files:
            code_name = file.split(".")[0]
            code = code_name.split("-")[0]
            name = code_name.split("-")[1]
            appender = (code, name)
            stocks.append(appender)
        return stocks


# 读取本地数据文件
def read_data(stock, name):
    file_name = stock + '-' + name + '.h5'
    try:
        return pd.read_hdf(DATA_DIR + "/" + file_name)
    except FileNotFoundError:
        return


# 是否需要更新数据
def need_update_data():
    filename = "data/000001-平安银行.h5"
    last_modified = os.stat(filename).st_mtime
    now = time.time()
    time_diff = now - last_modified
    return time_diff > ONE_HOUR_SECONDS


# 是否是工作日
def is_weekday():
    return datetime.datetime.today().weekday() < 5
