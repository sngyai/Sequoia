# -*- encoding: UTF-8 -*-

import utils
from talib import ATR
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
settings.init()
# code_name = ('300623', '捷捷微电')
# code_name = ('600145', '*ST新亿')
# code_name = ('601700', '风范股份')
# code_name = ('000725', '京东方Ａ')
code_name = ('002157', '正邦科技')
# code_name = ('300663', '科蓝软件')
# end = '2017-09-26'
end = '2019-02-15'

data = utils.read_data(code_name)
# print(data)
result = enter.check_volume(code_name, data, end_date=end)
print("low atr check {0}'s result: {1}".format(code_name, result))
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
# print(data['high'].values)
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
