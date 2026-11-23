from datetime import datetime


def next_run(expr, after):
    """The first time strictly after `after` (a naive datetime) that matches the cron expression `expr`.

    `expr` has five space-separated fields: minute (0-59), hour (0-23), day of month (1-31), month (1-12) and
    day of week (0-7, where 0 and 7 are both Sunday). Each field is `*`, a number, a range `a-b`, a step
    `*/n` or `a-b/n`, or a comma-separated list of these. As in standard cron, when both day of month and
    day of week are restricted (neither is `*`), a day matches if either matches.
    The result has seconds and microseconds of zero. Anything invalid (a wrong number of fields, a value
    out of range, a step of 0, text that is not a number) raises ValueError.
    """
    raise NotImplementedError
