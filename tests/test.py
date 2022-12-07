# -*- encoding: UTF-8 -*-
import strategy.high_tight_flag
import utils
import strategy.enter as enter
import strategy.low_atr as low_atr
import strategy.enter as enter
import strategy.backtrace_ma250 as backtrace_ma250
import strategy.parking_apron as parking_apron
import strategy.breakthrough_platform as breakthrough_platform
import logging
import settings

# data = utils.load("000012.h5")
#
# rolling_window = 21
# moving_average = 20
#
# average_true_range_list = ATR(
#     data.high.values[-rolling_window:],
#     data.low.values[-rolling_window:],
#     data.close.values[-rolling_window:],
#     timeperiod=moving_average
# )
#
# average_true_range = average_true_range_list[-1]
#
from strategy import turtle_trade, high_tight_flag, climax_limitdown
from work_flow import process

settings.init()
# code_name = ('300623', '捷捷微电')
# code_name = ('600145', '*ST新亿')
# code_name = ('601700', '风范股份')
# code_name = ('000725', '京东方Ａ')
# code_name = ('300437', '清水源')
# # code_name = ('300663', '科蓝软件')
# # end = '2017-09-26'
# end = '2021-10-13'
#
# data = utils.read_data(code_name)
# # print(data)
# result = strategy.high_tight_flag.check(code_name, data, end_date=end)
# print("low atr check {0}'s result: {1}".format(code_name, result))
#
# rolling_window = 21
# moving_average = 20
#
# average_true_range = ATR(
#         data.high.values[-rolling_window:],
#         data.low.values[-rolling_window:],
#         data.close.values[-rolling_window:],
#         timeperiod=moving_average
#     )
# print(data['最高'].values)
#
# print(average_true_range)

# print(atr_list)
# atr = atr_list[-1]
# print(atr)
# print(enter.check_volume(stock, data, end_date="2018-01-02"))
# import notify
#
# results = ['300188', '600271']
# msg = '\n'.join("*代码：%s" % ''.join(x) for x in results)
# notice.push(msg)
# print(results)

# import tushare as ts
#
# data = ts.get_stock_basics()
# print(data)

stocks = [('002728', '特一药业')]
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

process(stocks, strategies)