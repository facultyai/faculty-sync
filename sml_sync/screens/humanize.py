# Largely stolen from https://github.com/jmoiron/humanize (MIT)

from datetime import datetime, timedelta


def _ngettext(message, plural, num):
    return message if num == 1 else plural


def _now():
    return datetime.now()


def abs_timedelta(delta):
    """Returns an "absolute" value for a timedelta, always representing a
    time distance."""
    if delta.days < 0:
        now = _now()
        return now - (now + delta)
    return delta


def date_and_delta(value):
    """Turn a value into a date and a timedelta which represents how long ago
    it was.  If that's not possible, return (None, value)."""
    now = _now()
    if isinstance(value, datetime):
        date = value
        delta = now - value
    elif isinstance(value, timedelta):
        date = now - value
        delta = value
    else:
        try:
            value = int(value)
            delta = timedelta(seconds=value)
            date = now - delta
        except (ValueError, TypeError):
            return (None, value)
    return date, abs_timedelta(delta)


def naturaldelta(value, months=True):
    """Given a timedelta or a number of seconds, return a natural
    representation of the amount of time elapsed.  This is similar to
    ``naturaltime``, but does not add tense to the result.  If ``months``
    is True, then a number of months (based on 30.5 days) will be used
    for fuzziness between years."""
    date, delta = date_and_delta(value)
    if date is None:
        return value

    use_months = months

    seconds = abs(delta.seconds)
    days = abs(delta.days)
    years = days // 365
    days = days % 365
    months = int(days // 30.5)

    if not years and days < 1:
        if seconds < 60:
            return "a moment"
        elif 60 <= seconds < 120:
            return "a minute"
        elif 120 <= seconds < 3600:
            minutes = seconds // 60
            return _ngettext("%d minute", "%d minutes", minutes) % minutes
        elif 3600 <= seconds < 3600 * 2:
            return "an hour"
        elif 3600 < seconds:
            hours = seconds // 3600
            return _ngettext("%d hour", "%d hours", hours) % hours
    elif years == 0:
        if days == 1:
            return "a day"
        if not use_months:
            return _ngettext("%d day", "%d days", days) % days
        else:
            if not months:
                return _ngettext("%d day", "%d days", days) % days
            elif months == 1:
                return "a month"
            else:
                return _ngettext("%d month", "%d months", months) % months
    elif years == 1:
        if not months and not days:
            return "a year"
        elif not months:
            return _ngettext("1 year, %d day", "1 year, %d days", days) % days
        elif use_months:
            if months == 1:
                return "1 year, 1 month"
            else:
                return (
                    _ngettext("1 year, %d month", "1 year, %d months", months)
                    % months
                )
        else:
            return _ngettext("1 year, %d day", "1 year, %d days", days) % days
    else:
        return _ngettext("%d year", "%d years", years) % years


def naturaltime(value, future=False, months=True):
    """Given a datetime or a number of seconds, return a natural representation
    of that time in a resolution that makes sense.  This is more or less
    compatible with Django's ``naturaltime`` filter.  ``future`` is ignored for
    datetimes, where the tense is always figured out based on the current time.
    If an integer is passed, the return value will be past tense by default,
    unless ``future`` is set to True."""
    now = _now()
    date, delta = date_and_delta(value)
    if date is None:
        return value
    # determine tense by value only if datetime/timedelta were passed
    if isinstance(value, (datetime, timedelta)):
        future = date > now

    ago = "%s from now" if future else "%s ago"
    delta = naturaldelta(delta, months)

    if delta == "a moment":
        return "now"

    return ago % delta


suffixes = ("kB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")


def naturalsize(value, format="%.1f"):
    """Format a number of byteslike a human readable filesize (eg. 10 kB) """

    base = 1024
    bytes = float(value)

    if bytes == 1:
        return "1 Byte"
    elif bytes < base:
        return "%d Bytes" % bytes

    for i, s in enumerate(suffixes):
        unit = base ** (i + 2)
        if bytes < unit:
            return (format + " %s") % ((base * bytes / unit), s)
    return (format + " %s") % ((base * bytes / unit), s)
