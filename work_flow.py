# -*- encoding: UTF-8 -*-

import data_fetcher
import utils
import strategy.enter as enter
from strategy import turtle_trade, climax_limitdown
from strategy import backtrace_ma250
from strategy import breakthrough_platform
from strategy import parking_apron
from strategy import low_backtrace_increase
from strategy import keep_increasing
from strategy import high_tight_flag
import akshare as ak
import push
import logging
import db
import time
import datetime
import urllib
import settings
import pandas as pd


def process():
    logging.info("************************ process start ***************************************")
    all_data = ak.stock_zh_a_spot_em()
    subset = all_data[['代码', '名称', '总市值']]
    stocks = [tuple(x) for x in subset.values]
    statistics(all_data, stocks)

    strategies = {
        '海龟交易法则': turtle_trade.check_enter,
        # '放量上涨': enter.check_volume,
        # '均线多头': keep_increasing.check,
        # '停机坪': parking_apron.check,
        # '回踩年线': backtrace_ma250.check,
        '高而窄的旗形': high_tight_flag.check,
        '放量跌停': climax_limitdown.check,
        # '突破平台': breakthrough_platform.check,
        # '无大幅回撤': low_backtrace_increase.check,
    }

    if datetime.datetime.now().weekday() == 0:
        strategies['均线多头'] = keep_increasing.check

    stocks_data = data_fetcher.run(stocks)
    for strategy, strategy_func in strategies.items():
        check(stocks_data, strategy, strategy_func)
        time.sleep(2)

    logging.info("************************ process   end ***************************************")


def check(stocks_data, strategy, strategy_func):
    end = None
    m_filter = check_enter(end_date=end, strategy_fun=strategy_func)
    results = dict(filter(m_filter, stocks_data.items()))
    if len(results) > 0:
        push.strategy('**************"{0}"**************\n{1}\n**************"{0}"**************\n'.format(strategy, results))


def check_enter(end_date=None, strategy_fun=enter.check_volume):
    def end_date_filter(stock_data):
        if end_date is not None:
            if end_date < stock_data[1].iloc[0].日期:  # 该股票在end_date时还未上市
                logging.debug("{}在{}时还未上市".format(stock_data[0], end_date))
                return False
        return strategy_fun(stock_data[0], stock_data[1], end_date=end_date)


    return end_date_filter


# 统计数据
def statistics(all_data, stocks):
    limitup = len(all_data.loc[(all_data['涨跌幅'] >= 9.5)])
    limitdown = len(all_data.loc[(all_data['涨跌幅'] <= -9.5)])

    up5 = len(all_data.loc[(all_data['涨跌幅'] >= 5)])
    down5 = len(all_data.loc[(all_data['涨跌幅'] <= -5)])

    def ma250(stock):
        stock_data = utils.read_data(stock)
        return enter.check_ma(stock, stock_data)

    ma250_count = len(list(filter(ma250, stocks)))

    msg = "涨停数：{}   跌停数：{}\n涨幅大于5%数：{}  跌幅大于5%数：{}\n年线以上个股数量：    {}"\
        .format(limitup, limitdown, up5, down5, ma250_count)
    push.statistics(msg)


