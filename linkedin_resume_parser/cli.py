from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

from .parser import parse_pdf


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Parse a LinkedIn profile PDF into JSON Resume schema."
    )
    parser.add_argument("pdf", type=Path, help="Path to LinkedIn PDF")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("resume.json"),
        help="Output JSON file path",
    )
    parser.add_argument(
        "--personal-info",
        type=Path,
        default=None,
        help="Optional personal_info.json to merge (phone, additional_skills).",
    )
    parser.add_argument(
        "--skills-csv",
        type=Path,
        default=None,
        help="Optional LinkedIn Skills.csv to merge into skills list.",
    )
    parser.add_argument(
        "--certifications-csv",
        type=Path,
        default=None,
        help="Optional LinkedIn Certifications.csv to enrich certificates.",
    )
    parser.add_argument(
        "--projects-csv",
        type=Path,
        default=None,
        help="Optional LinkedIn Projects.csv to enrich projects.",
    )
    return parser


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_name(value: str | None) -> str:
    return (value or "").strip()


def ensure_list(resume: dict, key: str) -> list[dict]:
    value = resume.get(key)
    if not isinstance(value, list):
        value = []
        resume[key] = value
    return value


def add_skill(resume: dict, name: str, existing: set[str]) -> bool:
    clean = normalize_name(name)
    if not clean:
        return False
    key = clean.lower()
    if key in existing:
        return False
    ensure_list(resume, "skills").append({"name": clean})
    existing.add(key)
    return True


def parse_year_month(value: str | None) -> str:
    raw = normalize_name(value)
    if not raw:
        return ""
    for fmt in ("%b %Y", "%B %Y", "%Y-%m", "%Y"):
        try:
            parsed = datetime.strptime(raw, fmt)
            return parsed.strftime("%Y-%m")
        except ValueError:
            continue
    try:
        parsed = datetime.fromisoformat(raw)
        return parsed.strftime("%Y-%m")
    except ValueError:
        return raw


def set_if_missing(entry: dict, key: str, value: str) -> bool:
    if not value:
        return False
    if not entry.get(key):
        entry[key] = value
        return True
    return False


def merge_personal_info(resume: dict, path: Path) -> bool:
    if not path.exists():
        return False
    personal = load_json(path)
    updated = False

    additional = personal.get("additional_skills") or []
    if isinstance(additional, list):
        existing = {
            normalize_name(entry.get("name")).lower()
            for entry in resume.get("skills", [])
            if isinstance(entry, dict)
        }
        for name in additional:
            if add_skill(resume, str(name), existing):
                updated = True

    phone = normalize_name(personal.get("phone"))
    if phone:
        basics = resume.setdefault("basics", {})
        if not basics.get("phone"):
            basics["phone"] = phone
            updated = True

    return updated


def merge_skills_csv(resume: dict, path: Path) -> bool:
    if not path.exists():
        return False
    existing = {
        normalize_name(entry.get("name")).lower()
        for entry in resume.get("skills", [])
        if isinstance(entry, dict)
    }
    updated = False
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if add_skill(resume, row.get("Name"), existing):
                updated = True
    return updated


def merge_certifications_csv(resume: dict, path: Path) -> bool:
    if not path.exists():
        return False
    certificates = ensure_list(resume, "certificates")
    existing = {
        normalize_name(entry.get("name")).lower(): entry
        for entry in certificates
        if isinstance(entry, dict)
    }
    updated = False
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            name = normalize_name(row.get("Name"))
            if not name:
                continue
            key = name.lower()
            issuer = normalize_name(row.get("Authority"))
            url = normalize_name(row.get("Url"))
            date_raw = normalize_name(row.get("Started On")) or normalize_name(
                row.get("Finished On")
            )
            date_value = parse_year_month(date_raw)

            if key in existing:
                entry = existing[key]
                if set_if_missing(entry, "issuer", issuer):
                    updated = True
                if set_if_missing(entry, "date", date_value):
                    updated = True
                if set_if_missing(entry, "url", url):
                    updated = True
                continue

            certificates.append(
                {
                    "name": name,
                    "issuer": issuer,
                    "date": date_value,
                    "url": url,
                }
            )
            existing[key] = certificates[-1]
            updated = True
    return updated


def merge_projects_csv(resume: dict, path: Path) -> bool:
    if not path.exists():
        return False
    projects = ensure_list(resume, "projects")
    existing = {
        normalize_name(entry.get("name")).lower(): entry
        for entry in projects
        if isinstance(entry, dict)
    }
    updated = False
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            name = normalize_name(row.get("Title"))
            if not name:
                continue
            key = name.lower()
            description = normalize_name(row.get("Description"))
            url = normalize_name(row.get("Url"))
            start_date = parse_year_month(row.get("Started On"))
            end_date = parse_year_month(row.get("Finished On"))

            if key in existing:
                entry = existing[key]
                if set_if_missing(entry, "description", description):
                    updated = True
                if set_if_missing(entry, "url", url):
                    updated = True
                if set_if_missing(entry, "startDate", start_date):
                    updated = True
                if set_if_missing(entry, "endDate", end_date):
                    updated = True
                continue

            projects.append(
                {
                    "name": name,
                    "description": description,
                    "url": url,
                    "startDate": start_date,
                    "endDate": end_date,
                }
            )
            existing[key] = projects[-1]
            updated = True
    return updated


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    resume = parse_pdf(str(args.pdf))
    updated = False
    if args.personal_info:
        updated = merge_personal_info(resume, args.personal_info) or updated
    if args.skills_csv:
        updated = merge_skills_csv(resume, args.skills_csv) or updated
    if args.certifications_csv:
        updated = merge_certifications_csv(resume, args.certifications_csv) or updated
    if args.projects_csv:
        updated = merge_projects_csv(resume, args.projects_csv) or updated
    args.output.write_text(json.dumps(resume, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
