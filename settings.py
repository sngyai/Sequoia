# -*- encoding: UTF-8 -*-
import yaml
import logging

def init():
    global config
    logging.basicConfig(format='%(asctime)s %(message)s', filename='sequoia.log')
    logging.getLogger().setLevel(logging.INFO)
    with open('config.yaml') as file:
        config = yaml.safe_load(file)
