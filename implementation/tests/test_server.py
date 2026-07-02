import json
import os
import sys
from pathlib import Path
import pytest

# Ensure implementation folder is in path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from db import SQLiteAdapter, ValidationError
from init_db import create_database
import mcp_server


@pytest.fixture(scope="module")
def test_db(tmp_path_factory):
    db_path = str(tmp_path_factory.mktemp("data") / "test_lab.db")
    create_database(db_path)
    return db_path


@pytest.fixture
def adapter(test_db):
    return SQLiteAdapter(test_db)


def test_list_tables(adapter):
    tables = adapter.list_tables()
    assert "students" in tables
    assert "courses" in tables
    assert "enrollments" in tables


def test_get_table_schema(adapter):
    schema = adapter.get_table_schema("students")
    col_names = [c["name"] for c in schema]
    assert "id" in col_names
    assert "name" in col_names
    assert "cohort" in col_names
    assert "gpa" in col_names


def test_search_valid(adapter):
    res = adapter.search("students", filters={"cohort": "A1"})
    assert res["count"] == 2
    for row in res["rows"]:
        assert row["cohort"] == "A1"


def test_search_ordering_and_pagination(adapter):
    res = adapter.search("students", order_by="gpa", descending=True, limit=2)
    assert len(res["rows"]) <= 2
    if len(res["rows"]) == 2:
        assert res["rows"][0]["gpa"] >= res["rows"][1]["gpa"]


def test_search_invalid_table(adapter):
    with pytest.raises(ValidationError):
        adapter.search("missing_table")


def test_search_invalid_column(adapter):
    with pytest.raises(ValidationError):
        adapter.search("students", filters={"hacker_col": "test"})


def test_search_invalid_operator(adapter):
    with pytest.raises(ValidationError):
        adapter.search("students", filters={"gpa": {"DROP TABLE": 3.0}})


def test_insert_valid(adapter):
    new_student = {
        "name": "Grace Hopper",
        "cohort": "C1",
        "email": "grace@vinuni.edu.vn",
        "gpa": 4.0,
    }
    res = adapter.insert("students", new_student)
    assert res["inserted_id"] is not None
    assert res["row"]["name"] == "Grace Hopper"
    assert res["row"]["gpa"] == 4.0


def test_insert_empty(adapter):
    with pytest.raises(ValidationError):
        adapter.insert("students", {})


def test_insert_invalid_column(adapter):
    with pytest.raises(ValidationError):
        adapter.insert("students", {"name": "Test", "fake_column": 123})


def test_aggregate_count(adapter):
    res = adapter.aggregate("students", metric="count")
    assert len(res["rows"]) == 1
    assert res["rows"][0]["value"] >= 6


def test_aggregate_avg_group_by(adapter):
    res = adapter.aggregate("enrollments", metric="avg", column="score", group_by="course_id")
    assert len(res["rows"]) > 0
    for r in res["rows"]:
        assert "value" in r
        assert "course_id" in r


def test_aggregate_invalid_metric(adapter):
    with pytest.raises(ValidationError):
        adapter.aggregate("students", metric="destroy", column="gpa")


def test_mcp_server_tools_and_resources():
    # Test server tools directly via exported functions
    res_search = mcp_server.search("courses")
    assert res_search["count"] >= 4

    res_schema = json.loads(mcp_server.database_schema())
    assert "tables" in res_schema
    assert "students" in res_schema["tables"]

    res_tbl = json.loads(mcp_server.table_schema("courses"))
    assert res_tbl["table"] == "courses"