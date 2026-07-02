import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Ensure local imports work regardless of working directory
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from db import SQLiteAdapter, ValidationError
from init_db import create_database
from fastmcp import FastMCP

# Initialize FastMCP Server
mcp = FastMCP("SQLite Lab MCP Server")

# Initialize DB adapter with absolute path
DEFAULT_DB_PATH = os.environ.get("LAB_DB_PATH", str(Path(__file__).parent.resolve() / "lab.db"))

# Ensure database file exists and is seeded
if not os.path.exists(DEFAULT_DB_PATH):
    create_database(DEFAULT_DB_PATH)

adapter = SQLiteAdapter(DEFAULT_DB_PATH)


@mcp.tool(
    name="search",
    description="Search records in a SQLite table. Supports filtering, selecting columns, sorting, and pagination.",
)
def search(
    table: str,
    columns: Optional[List[str]] = None,
    filters: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None,
    limit: int = 20,
    offset: int = 0,
    order_by: Optional[str] = None,
    descending: bool = False,
) -> Dict[str, Any]:
    """
    Search records in the database.
    - table: Name of the table (e.g. 'students', 'courses', 'enrollments').
    - columns: Optional list of column names to retrieve.
    - filters: Optional filtering conditions (dict or list of dicts).
    - limit: Maximum number of rows to return (default 20).
    - offset: Number of rows to skip (default 0).
    - order_by: Column name to sort by.
    - descending: Sort descending if True.
    """
    return adapter.search(
        table=table,
        columns=columns,
        filters=filters,
        limit=limit,
        offset=offset,
        order_by=order_by,
        descending=descending,
    )


@mcp.tool(
    name="insert",
    description="Insert a new record into a SQLite database table.",
)
def insert(
    table: str,
    values: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Insert a new row into the specified table.
    - table: Name of the table.
    - values: Dictionary mapping column names to values.
    """
    return adapter.insert(table=table, values=values)


@mcp.tool(
    name="aggregate",
    description="Compute aggregate metrics (count, avg, sum, min, max) over a table column.",
)
def aggregate(
    table: str,
    metric: str,
    column: Optional[str] = None,
    filters: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None,
    group_by: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Compute aggregate statistics on a table.
    - table: Name of the table.
    - metric: Aggregate function ('count', 'avg', 'sum', 'min', 'max').
    - column: Column name to aggregate over (can be '*' for count).
    - filters: Optional filtering conditions.
    - group_by: Optional column name to group results by.
    """
    return adapter.aggregate(
        table=table,
        metric=metric,
        column=column,
        filters=filters,
        group_by=group_by,
    )


@mcp.resource("schema://database")
def database_schema() -> str:
    """Return the full schema of all tables in the database as structured JSON."""
    tables = adapter.list_tables()
    full_schema = {}
    for table in tables:
        full_schema[table] = adapter.get_table_schema(table)
    return json.dumps({"database": os.path.basename(DEFAULT_DB_PATH), "tables": full_schema}, indent=2)


@mcp.resource("schema://table/{table_name}")
def table_schema(table_name: str) -> str:
    """Return the detailed schema definition for a specific table."""
    schema = adapter.get_table_schema(table_name)
    return json.dumps({"table": table_name, "columns": schema}, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SQLite Lab FastMCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "http"],
        default="stdio",
        help="Transport protocol to run the MCP server (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host for SSE/HTTP server",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for SSE/HTTP server",
    )
    args, unknown = parser.parse_known_args()

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    elif args.transport == "sse":
        mcp.run(transport="sse", host=args.host, port=args.port)
    elif args.transport == "http":
        mcp.run(transport="http", host=args.host, port=args.port)