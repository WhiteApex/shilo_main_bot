from __future__ import annotations

from urllib.parse import parse_qs


def parse_start_payload(payload: str | None) -> dict[str, str]:
    if not payload:
        return {}
    params = parse_qs(payload.replace(" ", ""))
    return {key: values[0] for key, values in params.items() if values}
