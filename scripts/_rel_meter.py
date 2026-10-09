"""Spend meter of the metered OpenAlex REL collectors (tickets 1652, 2041).

Moved out of ``catalog_rel_causal_search`` so the id-batched backfill reuses it
without importing an entry point.
"""

MISSING_COST_USD = 0.001


class Meter:
    """Lane spend summed from ``x-ratelimit-cost-usd``; the day's remaining
    budget from ``x-ratelimit-remaining-usd``."""

    def __init__(self, lane_cap, daily_floor):
        self.lane_cap, self.daily_floor = lane_cap, daily_floor
        self.spent, self.remaining, self.prepaid, self.requests = 0.0, None, None, 0

    def observe(self, headers):
        h = {k.lower(): v for k, v in (headers or {}).items()}
        self.requests += 1
        try:
            # a response without the header is charged a search page, so the cap still binds
            self.spent += float(h.get("x-ratelimit-cost-usd") or MISSING_COST_USD)
        except ValueError:
            pass
        for attr, key in (("remaining", "x-ratelimit-remaining-usd"),
                          ("prepaid", "x-ratelimit-prepaid-remaining-usd")):
            try:
                setattr(self, attr, float(h[key]))
            except (KeyError, ValueError):
                pass

    def stop_reason(self):
        if self.spent >= self.lane_cap:
            return f"budget: lane cap {self.lane_cap} USD reached"
        if self.remaining is not None and self.remaining < self.daily_floor:
            return f"budget: daily remaining below {self.daily_floor} USD"
        return ""
