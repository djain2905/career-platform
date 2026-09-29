"""Create (or re-apply) the Career Platform schema.

Usage:  python -m scripts.init_db
"""
from __future__ import annotations

from app.db import connect, database_path, init_schema


def main() -> None:
    conn = connect()
    try:
        init_schema(conn)
        tables = [
            r["name"]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
    finally:
        conn.close()
    print(f"Schema applied to {database_path()}")
    print(f"{len(tables)} tables: {', '.join(tables)}")


if __name__ == "__main__":
    main()
