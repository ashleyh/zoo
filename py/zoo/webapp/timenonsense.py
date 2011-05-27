from datetime import tzinfo, datetime, timedelta

class UTC(tzinfo):
    def utcoffset(self, dt):
        return timedelta(0)
    def tzname(self, dt):
        return "UTC"
    def dst(self, dt):
        return timedelta(0)

epoch = datetime(2010, 1, 1, 0, 0, 0, 0, UTC())

def now(when=None):
    if when is None:
        when = datetime.now(UTC())
    delta = (when - epoch).total_seconds()
    return delta
