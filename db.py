# -*- encoding: UTF-8 -*-

import shelve
import settings


class ShelvePersistence(object):
    """
    Shelve为DBM和Pickle的结合，以键值对的方式把复杂对象序列化到文件持久化或者缓存持久化
    """
    def open(self):
        return shelve.open(settings.config['db_dir'] + "/Positions")

    def load(self, key):
        try:
            shelve_file = shelve.open(settings.config['db_dir'] + "/Positions")
            if key in shelve_file:
                result = shelve_file[key]
            else:
                result = None
        finally:
            shelve_file.close()
        return result

    # obj格式：{'positions': positions, 'cost': cost}
    # 参数：
    #   positions持仓，格式[{bought_price1, bought_amount}, {bought_price2, bought_amount}..{bought_price4, bought_amount}]
    #   cost: 持仓总成本
    def save(self, code_name, last_close, position_size):
        stock = code_name[0]
        new_position = (last_close, position_size)
        new_cost = position_size * 100 * last_close

        old_data = self.load(stock)
        shelve_file = shelve.open(settings.config['db_dir'] + "/Positions")

        if old_data is None:
            shelve_file[stock] = {'code_name': code_name, 'positions': [new_position], 'cost': new_cost}
            shelve_file.close()
            return True
        else:
            positions = old_data['positions']
            if len(positions) < 4:
                positions.append(new_position)
                cost = old_data['cost'] + new_cost
                shelve_file[stock] = {'code_name': code_name, 'positions': positions, 'cost': cost}
                shelve_file.close()
                return True
            else:
                return False

    def positions(self):
        shelve_file = shelve.open(settings.config['db_dir'] + "/Positions")
        for key in shelve_file:
            print(key, shelve_file[key])

