# -*- encoding: UTF-8 -*-
import yaml
import os


def init():
    global config
    root_dir = os.path.dirname(os.path.abspath(__file__))  # This is your Project Root
    config_file = os.path.join(root_dir, 'config.yaml')
    with open(config_file, 'r') as file:
        config = yaml.safe_load(file)
