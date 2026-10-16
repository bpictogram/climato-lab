import json
import datetime


class DatetimeJSONEncoder(json.JSONEncoder):
    def default(self, obj) -> str:
        if isinstance(obj, datetime.datetime):
            return (
                obj
                .astimezone(datetime.UTC)
                .isoformat(timespec="seconds")
                .replace("+00:00", "Z")
            )

        return super().default(obj)


def pprint_dict(dictionary: dict) -> None:
    print(json.dumps(dictionary, cls=DatetimeJSONEncoder, indent=4))
    