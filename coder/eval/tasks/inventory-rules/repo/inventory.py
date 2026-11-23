class InsufficientStock(Exception):
    pass

class Inventory:
    def __init__(self):
        self.stock = {}

    def add(self, item, qty):
        self.stock[item] = self.stock.get(item, 0) + qty

    def remove(self, item, qty):
        self.stock[item] = self.stock.get(item, 0) - qty

    def total_value(self, prices):
        return sum(q * prices.get(i, 0) for i, q in self.stock.items())
