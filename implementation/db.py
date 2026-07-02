import sqlite3
from typing import Any, Dict, List, Optional, Union


class ValidationError(Exception):
    """Raised when a request cannot be safely executed."""
    pass


class SQLiteAdapter:
    """
    SQLite adapter for FastMCP server.
    Handles connection management, schema inspection, parameterized query execution,
    and strict validation against SQL injection and invalid inputs.
    """

    SUPPORTED_OPERATORS = {"=", "!=", "<", "<=", ">", ">=", "like", "in"}
    SUPPORTED_METRICS = {"count", "avg", "sum", "min", "max"}

    def __init__(self, db_path: str):
        self.db_path = db_path

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def list_tables(self) -> List[str]:
        with self.connect() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;"
            )
            return [row["name"] for row in cursor.fetchall()]

    def get_table_schema(self, table: str) -> List[Dict[str, Any]]:
        self._validate_table(table)
        with self.connect() as conn:
            cursor = conn.execute(f"PRAGMA table_info({table});")
            rows = cursor.fetchall()
            return [
                {
                    "cid": row["cid"],
                    "name": row["name"],
                    "type": row["type"],
                    "notnull": bool(row["notnull"]),
                    "default_value": row["dflt_value"],
                    "pk": bool(row["pk"]),
                }
                for row in rows
            ]

    def _validate_table(self, table: str) -> None:
        if not table or not isinstance(table, str):
            raise ValidationError("Table name must be a non-empty string.")
        valid_tables = self.list_tables()
        if table not in valid_tables:
            raise ValidationError(f"Unknown table name: '{table}'. Valid tables: {valid_tables}")

    def _validate_columns(self, table: str, columns: Optional[List[str]]) -> List[str]:
        schema = self.get_table_schema(table)
        valid_cols = {col["name"] for col in schema}
        if not columns:
            return list(valid_cols)
        for col in columns:
            if col not in valid_cols:
                raise ValidationError(f"Unknown column name: '{col}' in table '{table}'. Valid columns: {sorted(valid_cols)}")
        return columns

    def _parse_filters(self, table: str, filters: Optional[Union[Dict, List]]) -> tuple[str, List[Any]]:
        if not filters:
            return "", []

        schema = self.get_table_schema(table)
        valid_cols = {col["name"] for col in schema}

        clauses = []
        params = []

        # If filters is a dict: e.g., {"cohort": "A1"} or {"gpa": {">": 3.5}}
        if isinstance(filters, dict):
            for col, condition in filters.items():
                if col not in valid_cols:
                    raise ValidationError(f"Unknown filter column: '{col}' in table '{table}'.")

                if isinstance(condition, dict):
                    # e.g., {"gpa": {">": 3.5, "<=": 4.0}}
                    for op, val in condition.items():
                        op_lower = op.lower()
                        if op_lower not in self.SUPPORTED_OPERATORS:
                            raise ValidationError(f"Unsupported filter operator: '{op}'. Supported: {sorted(self.SUPPORTED_OPERATORS)}")
                        clauses.append(f"{col} {op.upper()} ?")
                        params.append(val)
                elif isinstance(condition, (list, tuple)):
                    # implicit IN
                    if not condition:
                        raise ValidationError(f"Filter value list for column '{col}' cannot be empty.")
                    placeholders = ", ".join(["?"] * len(condition))
                    clauses.append(f"{col} IN ({placeholders})")
                    params.extend(condition)
                else:
                    clauses.append(f"{col} = ?")
                    params.append(condition)

        # If filters is a list of dicts: e.g., [{"column": "cohort", "operator": "=", "value": "A1"}]
        elif isinstance(filters, list):
            for f in filters:
                if not isinstance(f, dict) or "column" not in f:
                    raise ValidationError("Filter list item must be a dict containing at least 'column'.")
                col = f["column"]
                if col not in valid_cols:
                    raise ValidationError(f"Unknown filter column: '{col}' in table '{table}'.")
                op = str(f.get("operator", "=")).lower()
                if op not in self.SUPPORTED_OPERATORS:
                    raise ValidationError(f"Unsupported filter operator: '{f.get('operator')}'. Supported: {sorted(self.SUPPORTED_OPERATORS)}")
                val = f.get("value")

                if op == "in":
                    if not isinstance(val, (list, tuple)) or not val:
                        raise ValidationError(f"Operator 'IN' requires a non-empty list of values for column '{col}'.")
                    placeholders = ", ".join(["?"] * len(val))
                    clauses.append(f"{col} IN ({placeholders})")
                    params.extend(val)
                else:
                    clauses.append(f"{col} {op.upper()} ?")
                    params.append(val)
        else:
            raise ValidationError("Filters must be a dictionary or a list of filter condition objects.")

        where_clause = " WHERE " + " AND ".join(clauses) if clauses else ""
        return where_clause, params

    def search(
        self,
        table: str,
        columns: Optional[List[str]] = None,
        filters: Optional[Union[Dict, List]] = None,
        limit: int = 20,
        offset: int = 0,
        order_by: Optional[str] = None,
        descending: bool = False,
    ) -> Dict[str, Any]:
        self._validate_table(table)
        validated_cols = self._validate_columns(table, columns)
        cols_sql = ", ".join(validated_cols)

        where_sql, params = self._parse_filters(table, filters)

        order_sql = ""
        if order_by:
            self._validate_columns(table, [order_by])
            direction = "DESC" if descending else "ASC"
            order_sql = f" ORDER BY {order_by} {direction}"

        try:
            limit_val = int(limit)
            offset_val = int(offset)
            if limit_val < 0 or offset_val < 0:
                raise ValueError()
        except (ValueError, TypeError):
            raise ValidationError("Limit and offset must be non-negative integers.")

        query = f"SELECT {cols_sql} FROM {table}{where_sql}{order_sql} LIMIT ? OFFSET ?;"
        params.extend([limit_val, offset_val])

        with self.connect() as conn:
            cursor = conn.execute(query, params)
            rows = [dict(row) for row in cursor.fetchall()]

        return {
            "table": table,
            "count": len(rows),
            "limit": limit_val,
            "offset": offset_val,
            "rows": rows,
        }

    def insert(self, table: str, values: Dict[str, Any]) -> Dict[str, Any]:
        self._validate_table(table)
        if not values or not isinstance(values, dict):
            raise ValidationError("Insert values must be a non-empty dictionary.")

        validated_cols = self._validate_columns(table, list(values.keys()))
        cols_sql = ", ".join(validated_cols)
        placeholders = ", ".join(["?"] * len(validated_cols))
        params = [values[col] for col in validated_cols]

        query = f"INSERT INTO {table} ({cols_sql}) VALUES ({placeholders});"

        with self.connect() as conn:
            try:
                cursor = conn.execute(query, params)
                inserted_id = cursor.lastrowid
            except sqlite3.Error as e:
                raise ValidationError(f"Database error during insert: {e}")

            # Retrieve the newly inserted row
            schema = self.get_table_schema(table)
            pk_col = next((col["name"] for col in schema if col["pk"]), None)
            if pk_col and inserted_id:
                select_cursor = conn.execute(f"SELECT * FROM {table} WHERE {pk_col} = ?;", (inserted_id,))
                inserted_row = dict(select_cursor.fetchone() or {})
            else:
                inserted_row = values

        return {
            "table": table,
            "inserted_id": inserted_id,
            "row": inserted_row,
        }

    def aggregate(
        self,
        table: str,
        metric: str,
        column: Optional[str] = None,
        filters: Optional[Union[Dict, List]] = None,
        group_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        self._validate_table(table)

        if not metric or not isinstance(metric, str) or metric.lower() not in self.SUPPORTED_METRICS:
            raise ValidationError(
                f"Unsupported aggregate metric: '{metric}'. Supported metrics: {sorted(self.SUPPORTED_METRICS)}"
            )
        metric_upper = metric.upper()

        if column is not None and column != "*":
            self._validate_columns(table, [column])
            col_sql = column
        else:
            if metric_upper != "COUNT":
                raise ValidationError(f"Metric '{metric_upper}' requires a specific column name.")
            col_sql = "*"

        where_sql, params = self._parse_filters(table, filters)

        group_sql = ""
        select_cols = f"{metric_upper}({col_sql}) AS value"
        if group_by:
            self._validate_columns(table, [group_by])
            group_sql = f" GROUP BY {group_by}"
            select_cols = f"{group_by}, {select_cols}"

        query = f"SELECT {select_cols} FROM {table}{where_sql}{group_sql};"

        with self.connect() as conn:
            cursor = conn.execute(query, params)
            rows = [dict(row) for row in cursor.fetchall()]

        return {
            "table": table,
            "metric": metric.lower(),
            "column": column or "*",
            "group_by": group_by,
            "rows": rows,
        }