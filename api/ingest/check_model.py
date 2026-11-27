"""Print the registered shadow-model version without secrets."""

import json
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    key = next(
        line.split("=", 1)[1].strip()
        for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines()
        if line.startswith("API_KEY=")
    )
    request = Request("http://localhost:8082/api/risk-model", headers={"X-API-Key": key})
    with urlopen(request, timeout=120) as response:
        body = json.loads(response.read().decode())
    registry = body["registry"]
    print(json.dumps({
        "version": registry.get("version"),
        "trigger": registry.get("trigger"),
        "trigger_ref": registry.get("trigger_ref"),
        "trained_at": registry.get("trained_at"),
        "rows": body.get("rows"),
        "positives": body.get("positives"),
        "top": [row["vessel_id"] for row in body.get("current", [])[:3]],
    }))


if __name__ == "__main__":
    main()
