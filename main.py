# -*- encoding: UTF-8 -*-

import utils
import logging
import work_flow
import settings

logging.basicConfig(format='%(asctime)s %(message)s', filename='sequoia.log', level=logging.DEBUG)


# EXEC_TIME="15:05"
# schedule.every().day.at(EXEC_TIME).do(job)
# while True:
#     schedule.run_pending()
#     time.sleep(1)
def job():
    if utils.is_weekday():
        work_flow.process()


settings.init()
work_flow.process()
