from decimal import Decimal


def split(total, weights):
    """Split an amount of money into parts proportional to `weights`, in whole cents, so that the parts add
    up to exactly `total`.

    `total` is a string or Decimal with at most two decimal places (more raises ValueError); `weights` are
    non-negative numbers with a positive sum (otherwise ValueError). Each part is first its exact share
    rounded down to the cent; the cents left over go one each to the parts with the largest remainders,
    earlier parts first when remainders tie. A negative total is split as its absolute value and every part
    negated. Returns a list of Decimals with two decimal places.
    """
    raise NotImplementedError
