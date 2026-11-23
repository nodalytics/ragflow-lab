from datetime import datetime as D
import pytest
from cron import next_run

def test_working_hours_skip_the_weekend():
    assert next_run("*/15 9-17 * * 1-5", D(2026, 1, 2, 17, 50)) == D(2026, 1, 5, 9, 0)

def test_strictly_after_and_seconds():
    assert next_run("5,10 * * * *", D(2026, 1, 1, 10, 10, 30)) == D(2026, 1, 1, 11, 5)
    assert next_run("* * * * *", D(2026, 1, 1, 10, 10)) == D(2026, 1, 1, 10, 11)

def test_month_rollover_and_leap_day():
    assert next_run("0 0 1 * *", D(2026, 1, 31, 12, 0)) == D(2026, 2, 1, 0, 0)
    assert next_run("30 2 29 2 *", D(2026, 3, 1)) == D(2028, 2, 29, 2, 30)

def test_day_of_month_or_day_of_week():
    assert next_run("0 12 1 * 1", D(2026, 1, 1, 12, 0)) == D(2026, 1, 5, 12, 0)

def test_sunday_is_0_and_7():
    assert next_run("0 0 * * 7", D(2026, 1, 1)) == D(2026, 1, 4)
    assert next_run("0 0 * * 0", D(2026, 1, 1)) == D(2026, 1, 4)

def test_ranges_with_steps_and_lists():
    assert next_run("0 8-18/5 * * *", D(2026, 1, 1, 13, 1)) == D(2026, 1, 1, 18, 0)
    assert next_run("0 0 * 3,6 *", D(2026, 1, 1)) == D(2026, 3, 1)

@pytest.mark.parametrize("bad", ["60 * * * *", "* * *", "*/0 * * * *", "a * * * *", "* 24 * * *", "* * 0 * *",
                                 "* * * 13 *", "* * * * 8", "5-1 * * * *"])
def test_invalid(bad):
    with pytest.raises(ValueError):
        next_run(bad, D(2026, 1, 1))
