# -*- encoding: UTF-8 -*-
import yaml
import os
import tushare as ts


def init():
    global config
    global top_list
    root_dir = os.path.dirname(os.path.abspath(__file__))  # This is your Project Root
    config_file = os.path.join(root_dir, 'config.yaml')
    with open(config_file, 'r') as file:
        config = yaml.safe_load(file)
    df = ts.inst_tops(days=60)
    mask = (df['bcount'] > 1)  # 机构买入次数大于1
    df = df.loc[mask]
    top_list = df['code'].tolist()


def config():
    return config