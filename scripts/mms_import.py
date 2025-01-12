#!/usr/bin/env python
"""OpenNEM AEMO MMS Importer

Imports MMS data sets for any range into a local database schema

See also: mirror_mms.sh to dodwnload archives
"""

import gc
import logging
from pathlib import Path
from typing import List, Optional

import click

from opennem.core.parsers.aemo import AEMOTableSchema, AEMOTableSet, parse_aemo_csv
from opennem.db import get_database_engine
from opennem.db.models import mms
from opennem.pipelines.bulk_insert import build_insert_query
from opennem.pipelines.csv import generate_csv_from_records
from opennem.settings import settings  # noq
from opennem.utils.handlers import open

logger = logging.getLogger("opennem.mms")

MMA_PATH = Path(__file__).parent / "data" / "mms"


def find_available_mms_sets() -> List[str]:
    pass


MMS_MODELS = [
    getattr(mms, item) for item in dir(mms) if hasattr(getattr(mms, item), "__tablename__")
]


def get_mms_model(table: AEMOTableSchema) -> Optional[mms.Base]:

    table_lookup = list(
        filter(
            lambda x: x.__tablename__ == table.full_name or x.__tablename__ == table.name,
            MMS_MODELS,
        )
    )

    if not table_lookup:
        logger.error("Could not find ORM model for table {}".format(table.full_name))
        return None

    return table_lookup.pop()


def store_mms_table(table: AEMOTableSchema) -> int:

    if not table.name:
        logger.error("Table has no name!: {}".format(table))
        return 0

    # Get the table ORM model
    table_schema = get_mms_model(table)

    if not table_schema:
        raise Exception("No table ORM schema for table name {}".format(table.name))

    # update all non-primary key fields. get them dynamically.
    update_fields = [i.name for i in table_schema.__table__.columns if not i.primary_key]  # type: ignore

    records_to_store = table.records

    sql_query = build_insert_query(table_schema, update_fields)

    conn = get_database_engine().raw_connection()
    cursor = conn.cursor()
    csv_content = generate_csv_from_records(
        table_schema,
        records_to_store,
        column_names=records_to_store[0].keys(),
    )

    cursor.copy_expert(sql_query, csv_content)
    conn.commit()

    logger.info("Inserted {} records".format(len(records_to_store)))

    return len(records_to_store)


@click.command()
# @click.option("--purge", is_flag=True, help="Purge unmapped views")
def main() -> None:
    MMS_DIR = "data/mms/2021/MMSDM_2021_03/MMSDM_Historical_Data_SQLLoader/DATA/"

    mmsdir = Path(MMS_DIR)
    file_count: int = 0

    if not mmsdir.is_dir():
        raise Exception("Not a directory: {}".format(MMS_DIR))

    ts = AEMOTableSet()
    content = None

    for f in mmsdir.glob("*.zip"):
        with open(f) as fh:
            content = fh.read()

        ts = parse_aemo_csv(content)
        file_count += 1

        logger.info("Loaded {} files and {} tables".format(file_count, len(ts.table_names)))

        for table in ts.tables:
            logger.info("Storing table: {}".format(table.full_name))
            store_mms_table(table)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.error("User interrupted")
    except Exception as e:
        logger.error(e)

        if settings.debug:
            import traceback

            traceback.print_exc()

    finally:
        gc.collect()
