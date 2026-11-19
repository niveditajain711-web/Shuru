from app.utils.rate_limit import RateLimiter


def test_blocks_after_the_limit_and_counts_clients_separately():
    limiter = RateLimiter(2, 3600)

    assert limiter.allow("a") and limiter.allow("a")
    assert not limiter.allow("a")
    assert limiter.allow("b")


def test_forgets_clients_whose_window_has_passed(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr("app.utils.rate_limit.time.monotonic", lambda: now[0])
    limiter = RateLimiter(1, 60)
    limiter.allow("old-client")

    now[0] += 120  # the window has passed
    limiter.allow("new-client")

    assert set(limiter._hits) == {"new-client"}
