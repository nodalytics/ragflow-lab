# Inventory rules

- Quantities are whole numbers; adding or removing a quantity of zero or less raises ValueError.
- Removing more than is in stock raises InsufficientStock (defined in inventory.py) and changes nothing.
- Removing an item that was never added raises KeyError.
- An item whose stock reaches zero is removed from the inventory entirely.
- `total_value(prices)` is the sum of stock times price over all items; an item missing from `prices`
  raises KeyError.
