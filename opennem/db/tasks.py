from opennem.db import get_database_engine
from opennem.utils.dates import subtract_days

TIMESCALE_VIEWS = ["mv_facility_energy_hour"]

MATERIAL_VIEWS = ["mv_facility_all"]


def refresh_timescale_views() -> None:
    """refresh timescale views"""
    __query = "CALL refresh_continuous_aggregate('{view}', '{date_from}'::timestamp with time zone, null);"

    engine = get_database_engine()

    dt = subtract_days()
    date_from = dt.strftime("%Y-%m-%d %H:%M:%S+%Z")
    date_from = date_from.replace("UTC", "00")

    with engine.connect() as c:
        for v in TIMESCALE_VIEWS:
            query = __query.format(view=v, date_from=date_from)
            print(query)
            c.execution_options(isolation_level="AUTOCOMMIT").execute(query)


def refresh_material_views() -> None:
    """Refresh material views"""
    __query = "REFRESH MATERIALIZED VIEW CONCURRENTLY {view} with data"

    engine = get_database_engine()

    with engine.connect() as c:
        for v in MATERIAL_VIEWS:
            query = __query.format(view=v)
            c.execution_options(isolation_level="AUTOCOMMIT").execute(query)


def refresh_views() -> None:
    # refresh_timescale_views()
    refresh_material_views()


if __name__ == "__main__":
    refresh_timescale_views()