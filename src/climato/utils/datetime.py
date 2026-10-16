import datetime


def utc_now_iso() -> str:
    return (
        datetime.datetime.now(datetime.UTC)
        .strftime("%Y%m%dT%H%M%SZ")
    )


def utc_now_micro() -> str:
    return (
        datetime.datetime.now(datetime.UTC)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )
