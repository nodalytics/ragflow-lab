import os, time
os.environ["TZ"] = "America/New_York"
time.tzset()
from report import daily_counts

def test_counts_by_utc_day():
    # 2026-01-01 23:30 UTC and 2026-01-02 00:30 UTC
    assert daily_counts([1767310200, 1767313800]) == {"2026-01-01": 1, "2026-01-02": 1}
