from typing import List

from opennem.core.loader import load_data
from opennem.schema.time import TimeInterval, TimePeriod

SUPPORTED_PERIODS = ["7D", "1M", "1Y", "ALL"]

SUPPORTED_INTERVALS = ["5M", "15M", "30M", "1D", "1H", "1M"]


def load_intervals() -> List[TimeInterval]:
    interval_dicts = load_data("intervals.json")

    intervals = [TimeInterval(**i) for i in interval_dicts]

    return intervals


def load_periods() -> List[TimePeriod]:
    period_dicts = load_data("periods.json")

    periods = [TimePeriod(**i) for i in period_dicts]

    return periods


INTERVALS = load_intervals()

PERIODS = load_periods()


def get_interval(interval_human: str) -> TimeInterval:
    interval_lookup = list(
        filter(lambda x: x.interval_human == interval_human, INTERVALS)
    )

    if interval_lookup:
        return interval_lookup.pop()

    raise Exception("Invalid interval {} not mapped".format(interval_human))


def get_period(period_human: str) -> TimePeriod:
    period_lookup = list(
        filter(lambda x: x.period_human == period_human, PERIODS)
    )

    if period_lookup:
        return period_lookup.pop()

    raise Exception("Invalid interval {} not mapped".format(period_human))

