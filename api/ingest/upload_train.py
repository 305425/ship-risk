"""Upload data/train to the running API so the shadow model retrains."""

import json
import uuid
from pathlib import Path
from urllib.request import Request, urlopen

from app.schemas import TABLE_SPECS

ROOT = Path(__file__).resolve().parents[2]
TRAIN = ROOT / "data" / "train"
ENV = ROOT / ".env"


def _api_key() -> str:
    for line in ENV.read_text(encoding="utf-8").splitlines():
        if line.startswith("API_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("API_KEY is missing")


def _body() -> tuple[bytes, str]:
    boundary = uuid.uuid4().hex
    chunks: list[bytes] = []
    for spec in TABLE_SPECS.values():
        path = TRAIN / f"{spec.file_stem}.csv"
        chunks.append(f"--{boundary}\r\n".encode())
        chunks.append(f'Content-Disposition: form-data; name="files"; filename="{path.name}"\r\n'.encode())
        chunks.append(b"Content-Type: text/csv\r\n\r\n")
        chunks.append(path.read_bytes())
        chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), boundary


def main() -> None:
    payload, boundary = _body()
    request = Request(
        "http://localhost:8082/api/upload",
        data=payload,
        method="POST",
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "X-API-Key": _api_key(),
            "X-User": "dataset",
        },
    )
    with urlopen(request, timeout=180) as response:
        body = json.loads(response.read().decode())
    print(json.dumps({
        "status": response.status,
        "batch_id": body.get("batch_id"),
        "model": body.get("model"),
        "files": [item.get("file") or item.get("table") for item in body.get("files", [])],
    }))


if __name__ == "__main__":
    main()
