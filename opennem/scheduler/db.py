# pylint: disable=no-name-in-module
# pylint: disable=no-self-argument
# pylint: disable=no-member
import platform

from huey import PriorityRedisHuey, crontab

from opennem.db.tasks import refresh_material_views
from opennem.settings import settings
from opennem.workers.energy import run_energy_update_yesterday
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


@huey.periodic_task(crontab(hour="23,3,7,11,15,19", minute="45"))
@huey.lock_task("db_refresh_material_views")
def db_refresh_material_views() -> None:
    if settings.workers_db_run:
        refresh_material_views()


# @NOTE optimized can now run every hour but shouldn't have to
@huey.periodic_task(crontab(hour="*/1", minute="15"))
@huey.lock_task("db_refrehs_energies_yesterday")
def db_refrehs_energies_yesterday() -> None:
    if settings.workers_run:
        run_energy_update_yesterday()


@huey.periodic_task(crontab(hour="1"))
def db_facility_seen_update() -> None:
    if settings.workers_db_run:
        update_facility_seen_range()
