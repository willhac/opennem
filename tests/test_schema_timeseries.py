from datetime import date, datetime
from typing import Union

import pytest

from opennem.api.time import human_to_interval, human_to_period
from opennem.schema.dates import TimeSeries
from opennem.schema.network import NetworkNEM

start_dt = datetime.fromisoformat("1997-05-05 12:45:00+00:00")
end_dt = datetime.fromisoformat("2021-01-15 12:45:00+00:00")
end_dt2 = datetime.fromisoformat("2020-02-15 12:45:00+00:00")


@pytest.mark.parametrize(
    ["ts", "start_expected", "end_expected", "interval_expected", "length_expected"],
    [
        (
            TimeSeries(
                start=start_dt,
                end=end_dt,
                network=NetworkNEM,
                interval=NetworkNEM.get_interval(),
                period=human_to_period("7d"),
            ),
            # Also testing timezone shift from UTC to NEM time
            datetime.fromisoformat("2021-01-08 22:50:00+10:00"),
            datetime.fromisoformat("2021-01-15 22:45:00+10:00"),
            "5m",
            2016,  # number of 5 minute intervals in a year
        ),
        # Years
        (
            TimeSeries(
                start=start_dt,
                end=end_dt,
                network=NetworkNEM,
                year=2021,
                interval=human_to_interval("1d"),
                period=human_to_period("1Y"),
            ),
            # Expected
            datetime.fromisoformat("2021-01-01 00:00:00+00:00").date(),
            datetime.fromisoformat("2021-01-15 12:45:00+00:00").date(),
            "1d",
            15,
        ),
        (
            TimeSeries(
                start=start_dt,
                end=datetime.fromisoformat("2021-02-15 12:45:00+00:00"),
                network=NetworkNEM,
                year=2021,
                interval=human_to_interval("1d"),
                period=human_to_period("1Y"),
            ),
            # Expected
            datetime.fromisoformat("2021-01-01 00:00:00+00:00").date(),
            datetime.fromisoformat("2021-02-15 12:45:00+00:00").date(),
            "1d",
            46,
        ),
        (
            TimeSeries(
                start=start_dt,
                end=datetime.fromisoformat("2021-02-15 12:45:00+00:00"),
                network=NetworkNEM,
                year=2019,
                interval=human_to_interval("1d"),
                period=human_to_period("1Y"),
            ),
            # Expected
            datetime.fromisoformat("2019-01-01 00:00:00+00:00").date(),
            datetime.fromisoformat("2019-12-31 00:00:00+00:00").date(),
            "1d",
            365,
        ),
        (
            TimeSeries(
                start=start_dt,
                end=datetime.fromisoformat("2021-02-15 12:45:00+00:00"),
                network=NetworkNEM,
                year=2020,
                interval=human_to_interval("1d"),
                period=human_to_period("1Y"),
            ),
            # Expected
            datetime.fromisoformat("2020-01-01 00:00:00+00:00").date(),
            datetime.fromisoformat("2020-12-31 00:00:00+00:00").date(),
            "1d",
            366,  # leap year
        ),
        # All
        (
            TimeSeries(
                start=start_dt,
                end=end_dt2,
                network=NetworkNEM,
                interval=human_to_interval("1M"),
                period=human_to_period("all"),
            ),
            # Expected results
            datetime.fromisoformat("1997-05-01 00:00:00+00:00").date(),
            datetime.fromisoformat("2020-01-31 00:00:00+00:00").date(),
            "1M",
            274,
        ),
    ],
)
def test_schema_timeseries(
    ts: TimeSeries,
    start_expected: Union[datetime, date],
    end_expected: Union[datetime, date],
    interval_expected: str,
    length_expected: int,
) -> None:
    subject_daterange = ts.get_range()

    assert subject_daterange.start == start_expected, "Start matches"
    assert str(subject_daterange.start) == str(start_expected), "Start string matches"
    assert subject_daterange.end == end_expected, "End matches"
    assert str(subject_daterange.end) == str(end_expected), "End string matches"
    assert subject_daterange.trunc == interval_expected, "Interval matches"
    assert subject_daterange.length == length_expected, "Correct length"