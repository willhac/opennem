import decimal
import json
from datetime import datetime

from smart_open import open
from sqlalchemy.orm import sessionmaker

from opennem.db import db_connect
from opennem.db.models.opennem import FuelTech
from opennem.db.models.wem import WemFacility, metadata
from opennem.pipelines.wem import DatabaseStore, PipelineWemFacilityScada

engine = db_connect()
session = sessionmaker(bind=engine)


class NemEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return float(o)
        if isinstance(o, datetime):
            return o.isoformat()
        return super(NemEncoder, self).default(o)


def wem_7_days():
    __query = """
        select
            wfs.trading_interval,
            wf.fueltech_id,
            sum(wfs.generated) as gen,
            max(wfs.trading_interval) as latest_date,
            min(wfs.trading_interval)
        from wem_facility_scada wfs
        left join wem_facility wf on wfs.facility_id = wf.code
        where wf.fueltech_id is not NULL
        group by wfs.trading_interval, wf.fueltech_id
        having wfs.trading_interval > max(wfs.trading_interval) - interval '7 days'
        order by fueltech_id asc, wfs.trading_interval desc
        """

    json_envelope = []
    json_obj = None

    with engine.connect() as c:
        rows = c.execute(__query)

        current_tech = None

        for row in rows:

            if current_tech != row[1]:

                if json_obj is not None:
                    json_envelope.append(json_obj)

                current_tech = row[1]

                json_obj = {
                    "id": f"wa.fuel_tech.{current_tech}.energy",
                    "fuel_tech": current_tech,
                    "region": "wa",
                    "type": "energy",
                    "units": "mwh",
                    "history": {
                        "interval": "5m",
                        "last": row[3],
                        "start": row[4].isoformat(),
                        "data": [],
                    },
                }

            json_obj["history"]["data"].append(row[2])

    with open("wa1.json", "w") as fh:
        json.dump(json_envelope, fh, cls=NemEncoder)


if __name__ == "__main__":
    wem_7_days()
