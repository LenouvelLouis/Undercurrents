import pytest

from undercurrents.ingestion.setlistfm_client import RateLimiter


def test_rate_limiter_sleeps_when_called_too_soon():
    time_values = iter([100.0, 100.2, 100.2])
    def time_fn():
        return next(time_values)
    sleep_calls = []

    limiter = RateLimiter(min_interval=0.5, time_fn=time_fn, sleep_fn=sleep_calls.append)
    limiter.wait()
    limiter.wait()

    assert sleep_calls == [pytest.approx(0.3)]


def test_rate_limiter_does_not_sleep_when_enough_time_passed():
    time_values = iter([100.0, 101.0])
    def time_fn():
        return next(time_values)
    sleep_calls = []

    limiter = RateLimiter(min_interval=0.5, time_fn=time_fn, sleep_fn=sleep_calls.append)
    limiter.wait()
    limiter.wait()

    assert sleep_calls == []
