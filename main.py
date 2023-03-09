# -*- encoding: UTF-8 -*-

import utils
import logging
import work_flow
import settings
import schedule
import time
import datetime


def job():
    if utils.is_weekday():
        work_flow.prepare()


current_time = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
log_filename = 'logs/sequoia-{}.log'.format(current_time)
logging.basicConfig(format='%(asctime)s %(message)s', filename=log_filename)
logging.getLogger().setLevel(logging.INFO)
settings.init()

if settings.config['cron']:
    EXEC_TIME = "15:15"
    schedule.every().day.at(EXEC_TIME).do(job)

    while True:
        schedule.run_pending()
        time.sleep(1)
else:
    work_flow.prepare()
