class InsufficientStock(Exception):
    pass

class Inventory:
    def __init__(self):
        self.stock = {}

    def add(self, item, qty):
        if qty <= 0:
            raise ValueError("quantity must be positive")
        self.stock[item] = self.stock.get(item, 0) + qty

    def remove(self, item, qty):
        if qty <= 0:
            raise ValueError("quantity must be positive")
        if item not in self.stock:
            raise KeyError(item)
        if qty > self.stock[item]:
            raise InsufficientStock(item)
        self.stock[item] -= qty
        if self.stock[item] == 0:
            del self.stock[item]

    def total_value(self, prices):
        return sum(q * prices[i] for i, q in self.stock.items())
