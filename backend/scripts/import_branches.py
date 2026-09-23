from __future__ import annotations

from pathlib import Path

from app.services.branch_import import import_branches_csv


def main() -> None:
    csv_path = Path(__file__).resolve().parents[2] / "files" / "Branches.csv"
    imported = import_branches_csv(csv_path)
    print(f"Successfully imported {len(imported)} branch records from {csv_path}")


if __name__ == "__main__":
    main()
