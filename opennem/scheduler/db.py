# pylint: disable=no-name-in-module
# pylint: disable=no-self-argument
# pylint: disable=no-member
import platform

from huey import PriorityRedisHuey, crontab

from opennem.api.export.map import PriorityType
from opennem.api.export.tasks import export_energy
from opennem.db.tasks import refresh_material_views
from opennem.monitors.aemo_intervals import aemo_wem_live_interval
from opennem.monitors.database import check_database_live
from opennem.monitors.emissions import alert_missing_emission_factors
from opennem.monitors.facility_seen import facility_first_seen_check
from opennem.monitors.opennem import check_opennem_interval_delays
from opennem.notifications.slack import slack_message
from opennem.settings import settings  # noqa: F401
from opennem.utils.scrapyd import job_schedule_all
from opennem.workers.aggregates import run_aggregates_all
from opennem.workers.daily_summary import run_daily_fueltech_summary
from opennem.workers.energy import run_energy_update_days
from opennem.workers.facility_data_ranges import update_facility_seen_range

# Py 3.8 on MacOS changed the default multiprocessing model
if platform.system() == "Darwin":
    import multiprocessing

    try:
        multiprocessing.set_start_method("fork")
    except RuntimeError:
        # sometimes it has already been set by
        # other libs
        pass

redis_host = None

if settings.cache_url:
    redis_host = settings.cache_url.host

huey = PriorityRedisHuey("opennem.scheduler.db", host=redis_host)


# 5:45AM and 8:45AM AEST
@huey.periodic_task(crontab(hour="19", minute="45"))
def db_refresh_material_views() -> None:
    run_energy_update_days(days=2)
    run_aggregates_all()
    run_daily_fueltech_summary()
    refresh_material_views("mv_facility_all")
    refresh_material_views("mv_region_emissions")
    refresh_material_views("mv_interchange_energy_nem_region")
    export_energy(latest=True)
    export_energy(priority=PriorityType.monthly)
    slack_message("Ran daily energy update and aggregates on {}".format(settings.env))


@huey.periodic_task(crontab(hour="*/1", minute="15"))
@huey.lock_task("db_refresh_material_views_recent")
def db_refresh_material_views_recent() -> None:
    refresh_material_views("mv_facility_45d")
    refresh_material_views("mv_region_emissions_45d")


# @NOTE optimized can now run every hour but shouldn't have to
@huey.periodic_task(crontab(hour="*/3", minute="30"))
def db_refresh_energies_yesterday() -> None:
    run_energy_update_days(days=2)


# monitoring tasks
@huey.periodic_task(crontab(minute="*/60"), priority=80)
@huey.lock_task("monitor_opennem_intervals")
def monitor_opennem_intervals() -> None:
    for network_code in ["NEM", "WEM"]:
        check_opennem_interval_delays(network_code)


@huey.periodic_task(crontab(minute="*/60"), priority=50)
@huey.lock_task("monitor_wem_interval")
def monitor_wem_interval() -> None:
    aemo_wem_live_interval()


@huey.periodic_task(crontab(hour="12", minute="45"), priority=10)
@huey.lock_task("monitor_emission_factors")
def monitor_emission_factors() -> None:
    alert_missing_emission_factors()


@huey.periodic_task(crontab(hour="*", minute="*/1"))
def monitor_database() -> None:
    check_database_live()


# worker tasks
@huey.periodic_task(crontab(hour="23", minute="1"))
@huey.lock_task("schedule_facility_first_seen_check")
def schedule_facility_first_seen_check() -> None:
    """Check for new DUIDS"""
    facility_first_seen_check()


@huey.periodic_task(crontab(hour="4,10,16,22", minute="1"))
@huey.lock_task("db_facility_seen_update")
def db_facility_seen_update() -> None:
    if settings.workers_db_run:
        r = update_facility_seen_range()

        if r:
            slack_message("Ran facility seen range on {}".format(settings.env))


# spider tasks
@huey.periodic_task(crontab(hour="*/4", minute="55"))
@huey.lock_task("schedule_spider_catchup_tasks")
def spider_catchup_tasks() -> None:
    catchup_spiders = [
        "au.bom.capitals",
        "au.apvi.current",
        "au.nem.day.dispatch_is",
        "au.nem.day.dispatch_scada",
        "au.nem.day.rooftop",
        "au.nem.day.trading_is",
        "au.nem.week.dispatch",
        "au.nem.week.dispatch_actual_gen",
    ]

    for _spider_name in catchup_spiders:
        job_schedule_all(_spider_name)
