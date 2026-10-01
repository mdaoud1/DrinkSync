import json


def _optional_number(value):
    return value if isinstance(value, (int, float)) else None


def load_scale_config(path: str) -> dict:
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    if "offset" not in data or "referenceUnit" not in data:
        raise ValueError("scale config missing offset or referenceUnit")
    return {
        "offset": data["offset"],
        "referenceUnit": data["referenceUnit"],
        "initialMaxWeight": _optional_number(data.get("initialMaxWeight")),
        "lastWeight": _optional_number(data.get("lastWeight")),
    }


def save_scale_config(path: str, config: dict) -> None:
    payload = {
        "offset": config["offset"],
        "referenceUnit": config["referenceUnit"],
    }
    max_weight = _optional_number(config.get("initialMaxWeight"))
    last_weight = _optional_number(config.get("lastWeight"))
    if max_weight is not None:
        payload["initialMaxWeight"] = max_weight
    if last_weight is not None:
        payload["lastWeight"] = last_weight
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=4)
