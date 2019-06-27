# -*- encoding: UTF-8 -*-

import data_fetcher
import utils
import strategy.enter as enter
from strategy import turtle_trade
from strategy import backtrace_ma250
from strategy import breakthrough_platform
from strategy import parking_apron
from strategy import low_atr
import tushare as ts
import notify
import logging
import db
import settings


def process():
    logging.info("************************ process start ***************************************")
    if utils.need_update_data():
        utils.prepare()
        data_fetcher.run()
        check_exit()

    stocks = utils.get_stocks()
    m_filter = check_enter(end_date=None)
    results = list(filter(m_filter, stocks))

    statistics(stocks)

    logging.info('选股结果：{0}'.format(results))
    notify.notify('选股结果：{0}'.format(results))
    logging.info("************************ process   end ***************************************")


def check_enter(end_date=None):
    def end_date_filter(code_name):
        data = utils.read_data(code_name)
        # result = parking_apron.check(code_name, data, end_date=end_date)
        # result = low_atr.check_low_increase(code_name, data, end_date=end_date)
        # result = enter.check_ma(code_name, data, end_date=end_date)
        result = enter.check_volume(code_name, data, end_date=end_date)
                 # and enter.check_volume(code_name, data, end_date=end_date)
        if result:
            message = turtle_trade.calculate(code_name, data)
            logging.info("{0} {1}".format(code_name, message))
            notify.notify("{0} {1}".format(code_name, message))
        return result

    return end_date_filter


# 统计数据
def statistics(stocks):
    data = ts.get_today_all()
    limitup = len(data.loc[(data['changepercent'] >= 9.5)])
    limitdown = len(data.loc[(data['changepercent'] <= -9.5)])

    up5 = len(data.loc[(data['changepercent'] >= 5)])
    down5 = len(data.loc[(data['changepercent'] <= -5)])

    def ma250(stock):
        stock_data = utils.read_data(stock)
        return enter.check_ma(stock, stock_data)

    ma250_count = len(list(filter(ma250, stocks)))
    print(ma250_count)

    msg = "涨停数：{}   跌停数：{}\n涨幅大于5%数：{}  跌幅大于5%数：{}\n年线以上个股数量：    {}"\
        .format(limitup, limitdown, up5, down5, ma250_count)
    logging.info(msg)
    notify.statistics(msg)


def check_exit():
    t_shelve = db.ShelvePersistence()
    file = t_shelve.open()
    for key in file:
        code_name = file[key]['code_name']
        data = utils.read_data(code_name)
        if turtle_trade.check_exit(code_name, data):
            notify.notify("{0} 达到退出条件".format(code_name))
            logging.info("{0} 达到退出条件".format(code_name))
            del file[key]
        elif turtle_trade.check_stop(code_name, data, file[key]):
            notify.notify("{0} 达到止损条件".format(code_name))
            logging.info("{0} 达到止损条件".format(code_name))
            del file[key]

    file.close()

