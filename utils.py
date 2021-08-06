# -*- coding: UTF-8 -*-
import datetime
from pandas.tseries.offsets import *

import xlrd
import pandas as pd
import os
import settings

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
        data_files = os.listdir(settings.config['data_dir'])
        stocks = []
        for file in data_files:
            code_name = file.split(".")[0]
            code = code_name.split("-")[0]
            name = code_name.split("-")[1]
            appender = (code, name)
            stocks.append(appender)
        return stocks


def clean_files():
    for the_file in os.listdir(settings.config['data_dir']):
        file_path = os.path.join(settings.config['data_dir'], the_file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
        except Exception as e:
            print(e)


# 读取本地数据文件
def read_data(code_name):
    stock = code_name[0]
    name = code_name[1]
    file_name = stock + '-' + name + '.h5'
    if os.path.exists(settings.config['data_dir'] + "/" + file_name):
        return pd.read_hdf(settings.config['data_dir'] + "/" + file_name)
    else:
        return


# 是否需要更新数据
def need_update_data():
    try:
        code_name = ('000001', '平安银行')
        data = read_data(code_name)
        if data is None:
            return True
        else:
            start_time = next_weekday(data.iloc[-1].date)
            current_time = datetime.datetime.now()
            if start_time > current_time:
                return False
            return True
    except IOError:
        return True


# 是否是工作日
def is_weekday():
    return datetime.datetime.today().weekday() < 5


def next_weekday(date):
    return pd.to_datetime(date) + BDay()


def prepare():
    dirs = [settings.config['data_dir'], settings.config['db_dir']]
    for dir in dirs:
        if os.path.exists(dir):
            clean_files()
            return
        else:
            os.makedirs(dir)