# -*- coding: UTF-8 -*-

import xlrd
import pandas as pd
import os

DATA_DIR = 'data'


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


def read_data(stock, name):
    file_name = stock + '-' + name + '.h5'
    try:
        return pd.read_hdf(DATA_DIR + "/" + file_name)
    except FileNotFoundError:
        return

