from datetime import datetime as dt

import pytz
from dateutil.tz import gettz
from dateutil import parser


def gen_tzinfos():
    for zone in pytz.common_timezones:
        try:
            tzdate = pytz.timezone(zone).localize(dt.utcnow(), is_dst=None)
        except pytz.NonExistentTimeError:
            pass
        else:
            tzinfo = gettz(zone)

            if tzinfo:
                yield tzdate.tzname(), tzinfo


def parse_time(datetimestring: str):
    ret = parser.parse(datetimestring, tzinfos=dict(gen_tzinfos()))
    ret = ret.astimezone(pytz.utc)
    return ret
