from collections import OrderedDict
from datetime import datetime
from itertools import groupby
from operator import attrgetter
from typing import List, Optional

from sqlalchemy.orm import Session

from opennem.db.models.opennem import FacilityScada, Station
from opennem.schema.network import NetworkSchema
from opennem.schema.time import TimeInterval, TimePeriod
from opennem.schema.units import UnitDefinition
from opennem.utils.time import human_to_timedelta
from opennem.utils.timezone import make_aware

from .schema import (
    DataQueryResult,
    OpennemData,
    OpennemDataHistory,
    OpennemDataSet,
)


def stats_factory(
    stats: List[DataQueryResult],
    interval: TimeInterval,
    period: TimePeriod,
    network: NetworkSchema,
    units: UnitDefinition,
    code: str = None,
    region: str = None,
    fueltech_group: bool = False,
) -> Optional[OpennemDataSet]:
    """
        Takes a list of data query results and returns OpennemDataSets

        @TODO optional groupby field
        @TODO override timezone
    """

    network_timezone = network.get_timezone()

    dates = [s.interval for s in stats]
    start = make_aware(min(dates), network_timezone)
    end = make_aware(max(dates), network_timezone)

    # free
    dates = []

    group_codes = list(set([i.group_by for i in stats if i.group_by]))

    stats_grouped = []

    for group_code in group_codes:

        data_grouped = dict()

        for stat in stats:
            if stat.interval not in data_grouped:
                data_grouped[stat.interval] = None

            if stat.group_by == group_code:
                data_grouped[stat.interval] = stat.result

        data_sorted = OrderedDict(sorted(data_grouped.items()))

        history = OpennemDataHistory(
            start=start,
            last=end,
            interval=interval.interval_human,
            data=list(data_sorted.values()),
        )

        data = OpennemData(
            network=network.code,
            data_type=units.unit_type,
            units=units.unit,
            code=group_code,
            interval=interval,
            period=period,
            history=history,
        )

        # *sigh* - not the most flexible model
        if fueltech_group:
            data.fuel_tech = group_code
            data.id = ".".join(
                [network.code, "fueltech", group_code, units.unit_type]
            )
            # @TODO make this an alias
            data.type = units.unit_type

        if region:
            data.region = region

        stats_grouped.append(data)

    stat_set = OpennemDataSet(
        data_type=units.unit_type,
        data=stats_grouped,
        created_at=datetime.now(),
        code=code,
        network=network.code,
    )

    if region:
        stat_set.region = region

    return stat_set


def station_attach_stats(station: Station, session: Session) -> Station:
    # @TODO update for new queries
    since = datetime.now() - human_to_timedelta("7d")

    facility_codes = list(set([f.code for f in station.facilities]))

    stats = (
        session.query(FacilityScada)
        .filter(FacilityScada.facility_code.in_(facility_codes))
        .filter(FacilityScada.trading_interval >= since)
        .order_by(FacilityScada.facility_code)
        .order_by(FacilityScada.trading_interval)
        .all()
    )

    for facility in station.facilities:
        facility_power = list(
            filter(lambda s: s.facility_code == facility.code, stats)
        )

        # facility.scada_power = stats_factory(facility_power)

    return station
