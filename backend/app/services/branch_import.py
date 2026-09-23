from __future__ import annotations

import csv
import re
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

from sqlmodel import Session, SQLModel, select

from app.core.db import engine
from app.models.branch import Branch

COUNTRY_NAME_MAP = {
    "AU": "Australia",
    "CA": "Canada",
    "US": "United States",
}

PROVINCE_NAME_MAP = {
    "AB": "Alberta",
    "BC": "British Columbia",
    "MB": "Manitoba",
    "NB": "New Brunswick",
    "NL": "Newfoundland and Labrador",
    "NS": "Nova Scotia",
    "NT": "Northwest Territories",
    "NU": "Nunavut",
    "ON": "Ontario",
    "PE": "Prince Edward Island",
    "QC": "Quebec",
    "SK": "Saskatchewan",
    "YT": "Yukon",
    "ACT": "Australian Capital Territory",
    "NSW": "New South Wales",
    "NT": "Northern Territory",
    "QLD": "Queensland",
    "SA": "South Australia",
    "TAS": "Tasmania",
    "VIC": "Victoria",
    "WA": "Western Australia",
}


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    value = str(value).strip()
    return " ".join(value.split())


def _title_case(value: str) -> str:
    text = _clean_text(value)
    if not text:
        return ""
    return " ".join(part.capitalize() for part in text.split())


def _parse_int(value: Any) -> int | None:
    cleaned = _clean_text(value)
    if not cleaned:
        return None
    cleaned = cleaned.replace(",", "")
    if cleaned.lower() in {"n/a", "na", "null", "none"}:
        return None
    if re.fullmatch(r"[+-]?\d+", cleaned):
        return int(cleaned)
    return None


def _parse_float(value: Any) -> float | None:
    cleaned = _clean_text(value)
    if not cleaned:
        return None
    if cleaned.lower() in {"n/a", "na", "null", "none"}:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _normalize_country(value: Any) -> str:
    cleaned = _clean_text(value).upper()
    if not cleaned:
        return ""
    return COUNTRY_NAME_MAP.get(cleaned, cleaned.title())


def _normalize_region(value: Any, country: str) -> str:
    cleaned = _clean_text(value)
    if not cleaned:
        return country
    if cleaned.lower() in {"n/a", "na", "null"}:
        return country
    return cleaned


def _normalize_postal_code(value: Any) -> str:
    cleaned = _clean_text(value)
    if not cleaned:
        return ""
    cleaned = re.sub(r"\s+", " ", cleaned.upper())
    return cleaned


def _normalize_phone(value: Any) -> str | None:
    cleaned = _clean_text(value)
    if not cleaned:
        return None
    if cleaned.lower() in {"n/a", "na", "null", "none"}:
        return None
    cleaned = cleaned.replace("-", " ").replace("/", " ")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned[:15]


def _normalize_lob(value: Any) -> str | None:
    cleaned = _clean_text(value)
    if not cleaned:
        return None
    if cleaned.lower() in {"n/a", "na", "null", "none"}:
        return None
    return cleaned.split(",")[0].strip()


def _normalize_province(value: Any, country_code: str | None) -> str:
    if country_code is None:
        country_code = ""
    cleaned = _clean_text(value)
    if not cleaned:
        return ""
    code = cleaned.upper()
    if code in PROVINCE_NAME_MAP:
        return PROVINCE_NAME_MAP[code]
    if country_code.upper() in {"CA", "AU"}:
        return _title_case(cleaned)
    return cleaned.title()


def clean_branch_row(raw_row: Mapping[str, Any]) -> dict[str, Any]:
    country_code = _clean_text(raw_row.get("Branch Country"))
    country_name = _normalize_country(country_code)
    province_value = _normalize_province(raw_row.get("Branch Province"), country_code)
    name = _title_case(raw_row.get("Branch Name", ""))
    if not name:
        raise ValueError("Branch name is required")

    join_key = _parse_int(raw_row.get("BranchJoinKey"))
    if join_key is None:
        raise ValueError(f"Invalid join_key for branch '{name}'")

    normalized = {
        "name": name,
        "address1": _clean_text(raw_row.get("Address1")) or None,
        "address2": None,
        "city": _title_case(raw_row.get("Branch City", "")) or "Unknown",
        "postal_code": _normalize_postal_code(raw_row.get("PostalCode")) or "",
        "province": province_value or country_name,
        "country": country_name or "Unknown",
        "region": _normalize_region(raw_row.get("Region Name"), country_name),
        "latitude": _parse_float(raw_row.get("Latitude")),
        "longitude": _parse_float(raw_row.get("Longitude")),
        "join_key": join_key,
        "phone": _normalize_phone(raw_row.get("Telephone1")),
        "email": None,
        "website_url": None,
        "contact_person": None,
        "division_name": _clean_text(raw_row.get("Division Name")) or None,
        "lob_name": _normalize_lob(raw_row.get("LOBName")),
        "is_active": True,
    }

    return normalized


def iter_branch_csv_rows(csv_path: str | Path) -> Iterator[dict[str, Any]]:
    path = Path(csv_path)
    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            if not row:
                continue
            if all(_clean_text(value) == "" for value in row.values()):
                continue
            yield row


def import_branches_csv(csv_path: str | Path) -> list[Branch]:
    SQLModel.metadata.create_all(engine)

    imported: list[Branch] = []
    seen_join_keys: set[int] = set()

    with Session(engine) as session:
        for row in iter_branch_csv_rows(csv_path):
            try:
                cleaned = clean_branch_row(row)
            except ValueError:
                continue

            join_key = cleaned["join_key"]
            if join_key in seen_join_keys:
                continue
            seen_join_keys.add(join_key)

            existing = session.exec(
                select(Branch).where(Branch.join_key == join_key)
            ).first()
            if existing is not None:
                continue

            branch = Branch(**cleaned)
            session.add(branch)
            imported.append(branch)

        session.commit()
        for branch in imported:
            session.refresh(branch)

    return imported


def main() -> None:
    csv_path = Path(__file__).resolve().parents[2] / "files" / "Branches.csv"
    imported = import_branches_csv(csv_path)
    print(f"Imported {len(imported)} branches from {csv_path}")


if __name__ == "__main__":
    main()
