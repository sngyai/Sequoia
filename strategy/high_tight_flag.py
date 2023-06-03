# -*- encoding: UTF-8 -*-
import logging
import settings


# 高而窄的旗形
def check(code_name, data, end_date=None, threshold=60):
    # 龙虎榜上必须有机构
    if code_name[0] not in settings.top_list:
        return False

    if end_date is not None:
        mask = (data['日期'] <= end_date)
        data = data.loc[mask]
    data = data.tail(n=threshold)

    if len(data) < threshold:
        logging.debug("{0}:样本小于{1}天...\n".format(code_name, threshold))
        return False

    data = data.tail(n=14)
    low = data['最低'].min()
    ratio_increase = data.iloc[-1]['最高'] / low
    if ratio_increase < 1.9:
        return False

    previous_p_change = 0.0
    # 连续两天涨幅大于等于10%
    for _p_change in data['p_change'].values:
        if _p_change >= 9.5:
            if previous_p_change >= 9.5:
                return True
            else:
                previous_p_change = _p_change
        else:
            previous_p_change = 0.0

    return False
