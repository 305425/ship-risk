"""Synthetic inspection reports: one markdown file per inspection, written only from CSV facts.

Every report is labelled synthetic. The identity metadata for each file goes to
manifest.json, which ShipRiskRAG lays over the LLM's descriptive tags.
"""

import json
from pathlib import Path

import pandas as pd

from .rag import MANIFEST_NAME

SYNTHETIC_NOTICE = ("SYNTHETIC REPORT: generated from the uploaded CSV records for this prototype. "
                    "It is not a real PSC, class, flag or vetting report.")


def date_num(value) -> int | None:
    if value is None or pd.isna(value):
        return None
    return int(pd.Timestamp(value).strftime("%Y%m%d"))


def iso(value) -> str | None:
    if value is None or pd.isna(value):
        return None
    return pd.Timestamp(value).date().isoformat()


def _deficiency_line(d) -> str:
    status = (f"Closed on {iso(d.deficiency_closed_date)}" if d.deficiency_status == "Closed" else "Open")
    return (f"- {d.deficiency_id} {d.deficiency_code} ({d.deficiency_category}): "
            f"{d.deficiency_description}. Status: {status}.")


def build_reports(frames: dict[str, pd.DataFrame]) -> dict[str, tuple[str, dict]]:
    """file name -> (markdown, identity metadata)."""
    vessels = frames["vessels"].set_index("vessel_id")
    detentions = frames["detentions"].set_index("inspection_id")
    deficiencies = frames["deficiencies"]
    reports = {}
    for ins in frames["inspections"].sort_values("inspection_id").itertuples(index=False):
        v = vessels.loc[ins.vessel_id]
        when = iso(ins.inspection_date)
        defs = deficiencies[deficiencies["inspection_id"] == ins.inspection_id].sort_values("deficiency_id")
        open_count = int((defs["deficiency_status"] == "Open").sum())

        lines = [
            f"# {ins.inspection_type} inspection {ins.inspection_id}: {v.vessel_name} ({ins.vessel_id})",
            "",
            f"> {SYNTHETIC_NOTICE}",
            "",
            f"- Vessel: {v.vessel_name} ({ins.vessel_id}), IMO {v.imo_number}, {v.vessel_type}, "
            f"built {v.build_year}, flag {v.flag_state}",
            f"- Inspection: {ins.inspection_id}, {ins.inspection_type} inspection by {ins.inspection_authority} "
            f"at {ins.inspection_port} on {when}",
            f"- Result: {ins.inspection_result}",
        ]
        if ins.inspection_id in detentions.index:
            det = detentions.loc[ins.inspection_id]
            lines.append(f"- Detention: detained on {iso(det.detention_date)}. Reason: {det.detention_reason}")
        lines += ["", f"## Deficiencies ({len(defs)} raised, {open_count} still open)", ""]
        if defs.empty:
            lines.append("No deficiencies were recorded at this inspection.")
        else:
            lines += [_deficiency_line(d) for d in defs.itertuples(index=False)]
            categories = defs["deficiency_category"].value_counts()
            lines += ["", "## Summary", "",
                      f"{v.vessel_name} received {len(defs)} deficiencies at {ins.inspection_port} on {when}, "
                      f"mostly {', '.join(f'{c} ({n})' for c, n in categories.items())}. "
                      f"{open_count} remain open in the latest data."]

        identity = {
            "source_type": "report",
            "doc_type": "inspection_report",
            "evidence_id": f"report:{ins.inspection_id}",
            "record_id": ins.inspection_id,
            "vessel_id": ins.vessel_id,
            "vessel_name": v.vessel_name,
            "inspection_id": ins.inspection_id,
            "inspection_type": ins.inspection_type,
            "inspection_result": ins.inspection_result,
            "category": ins.inspection_authority.lower(),
            "date": when,
            "date_num": date_num(ins.inspection_date),
            "label": f"Inspection report {ins.inspection_id} (synthetic)",
            "synthetic": True,
        }
        reports[f"{ins.inspection_id}.md"] = ("\n".join(lines) + "\n", identity)
    return reports


def write_reports(reports_dir: Path, reports: dict[str, tuple[str, dict]]) -> dict:
    """Write reports and the manifest; only touch files whose content changed."""
    reports_dir.mkdir(parents=True, exist_ok=True)
    written = unchanged = 0
    for name, (text, _) in reports.items():
        path = reports_dir / name
        if path.exists() and path.read_text(encoding="utf-8") == text:
            unchanged += 1
            continue
        path.write_text(text, encoding="utf-8", newline="\n")
        written += 1
    removed = 0
    for path in reports_dir.glob("*.md"):
        if path.name not in reports:
            path.unlink()
            removed += 1
    manifest = {name: identity for name, (_, identity) in reports.items()}
    (reports_dir / MANIFEST_NAME).write_text(json.dumps(manifest, indent=1, sort_keys=True), encoding="utf-8")
    return {"written": written, "unchanged": unchanged, "removed": removed, "total": len(reports)}
