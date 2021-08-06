from settings import init
import settings


def test_load_config():
    init()
    print(settings.config['push'])
    print(settings.config['push']['url'])

