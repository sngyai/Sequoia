# -*- encoding: UTF-8 -*-
import logging


# 低回撤稳步上涨策略
def check(code_name, data, end_date=None, threshold=60):
    if end_date is not None:
        mask = (data['日期'] <= end_date)
        data = data.loc[mask]
    data = data.tail(n=threshold)

    if len(data) < threshold:
        logging.debug("{0}:样本小于{1}天...\n".format(code_name, threshold))
        return False

    ratio_increase = (data.iloc[-1]['收盘'] - data.iloc[0]['收盘']) / data.iloc[0]['收盘']
    if ratio_increase < 0.6:
        return False

    # 允许有一次“洗盘”
    flag = True
    for i in range(1, len(data)):
        # 单日跌幅超7%；高开低走7%；两日累计跌幅10%；两日高开低走累计10%
        if data.iloc[i - 1]['p_change'] < -7 \
                or (data.iloc[i]['收盘'] - data.iloc[i]['开盘'])/data.iloc[i]['开盘'] * 100 < -7 \
                or data.iloc[i - 1]['p_change'] + data.iloc[i]['p_change'] < -10 \
                or (data.iloc[i]['收盘'] - data.iloc[i - 1]['开盘']) / data.iloc[i - 1]['开盘'] * 100 < -10:
            return False
            # if flag:
            #     flag = False
            # else:
            #     return False

    return True
