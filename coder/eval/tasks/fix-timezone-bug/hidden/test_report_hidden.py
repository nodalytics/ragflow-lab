import os, time
os.environ["TZ"] = "Asia/Tokyo"
time.tzset()
from report import daily_counts, day_of

def test_counts_by_utc_day_any_local_zone():
    assert daily_counts([1767310200, 1767313800]) == {"2026-01-01": 1, "2026-01-02": 1}

def test_day_of_is_utc():
    assert day_of(0) == "1970-01-01"
