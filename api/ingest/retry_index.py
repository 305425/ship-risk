"""Ask the running API to index uploads still marked index_pending."""

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
    request = Request(
        "http://localhost:8082/api/index/retry",
        data=b"",
        method="POST",
        headers={"X-API-Key": key, "X-User": "retry"},
    )
    with urlopen(request, timeout=600) as response:
        body = json.loads(response.read().decode())
    print(json.dumps({"status": response.status, "skipped": body.get("skipped"), "reports": body.get("reports"), "records": body.get("records")}))


if __name__ == "__main__":
    main()
