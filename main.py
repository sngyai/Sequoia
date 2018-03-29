# -*- encoding: UTF-8 -*-

import process
import strategy.enter as enter
import utils
import notify


def strategy(end_date=None):
    def end_date_filter(stock):
        data = utils.read_data(stock)
        if data is None:
            return False
        return \
            enter.check_ma(stock, data, end_date=end_date) \
            and enter.check_volume(stock, data, end_date=end_date) \
            and enter.check_max_price(stock, data, end_date=end_date)
    return end_date_filter


process.run()
print("数据更新完毕！")
stocks = utils.get_stocks()

m_filter = strategy(end_date=None)

results = list(filter(m_filter, stocks))
msg = '\n'.join("*代码：%s" % ','.join(x) for x in results)
notify.notify(msg)
print(results)



