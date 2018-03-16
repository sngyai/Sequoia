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
        return table.col_values(0)[1:rows_count-1]
    else:
        data_files = os.listdir(DATA_DIR)
        stocks = [file.split(".")[0] for file in data_files]
        return stocks


def read_data(stock):
    try:
        return pd.read_hdf(DATA_DIR + "/" + stock + '.h5')
    except FileNotFoundError:
        return

