# -*- encoding: UTF-8 -*-

import utils
from talib import ATR
import strategy.enter as enter

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

stock = "601600"
data = utils.read_data(stock)

print(enter.check_ma(stock, data, end_date="2017-09-26"))

