# -*- coding: UTF-8 -*-

# 总市值
BALANCE = 200000


# 最后一个交易日收市价为指定区间内最高价
def check_enter(code_name, data, end_date=None, threshold=60):
    max_price = 0
    if end_date is not None:
        mask = (data['日期'] <= end_date)
        data = data.loc[mask]
    if data is None:
        return False
    data = data.tail(n=threshold)
    if len(data) < threshold:
        return False
    for index, row in data.iterrows():
        if row['收盘'] > max_price:
            max_price = float(row['收盘'])

    last_close = data.iloc[-1]['收盘']

    if last_close >= max_price:
        return True

    return False
