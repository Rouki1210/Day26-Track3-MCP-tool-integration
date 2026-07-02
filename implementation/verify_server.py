import asyncio
import json
import sys
import uuid
from pathlib import Path

# Ensure implementation directory is in sys.path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from db import ValidationError
import mcp_server


async def verify():
    print("======================================================")
    print("      Verifying SQLite Lab FastMCP Server")
    print("======================================================\n")

    passed = 0
    total = 0

    def check(name: str, condition: bool, msg: str = ""):
        nonlocal passed, total
        total += 1
        if condition:
            passed += 1
            print(f"[PASS] {name} {msg}")
        else:
            print(f"[FAIL] {name} {msg}")

    # 1. Check tool discovery
    tools = await mcp_server.mcp.list_tools()
    tool_names = {t.name for t in tools}
    check(
        "1. Tool Discovery",
        {"search", "insert", "aggregate"}.issubset(tool_names),
        f"(Discovered: {sorted(tool_names)})",
    )

    # 2. Check resource discovery
    resources = await mcp_server.mcp.list_resources()
    res_uris = {str(r.uri) for r in resources}
    check(
        "2. Resource Discovery",
        "schema://database" in res_uris,
        f"(Discovered resources: {sorted(res_uris)})",
    )

    # 3. Check resource template discovery
    templates = await mcp_server.mcp.list_resource_templates()
    tmpl_uris = {str(t.uri_template) for t in templates}
    check(
        "3. Resource Template Discovery",
        "schema://table/{table_name}" in tmpl_uris,
        f"(Discovered templates: {sorted(tmpl_uris)})",
    )

    # 4. Check valid tool calls
    try:
        search_res = mcp_server.search("students", filters={"cohort": "A1"})
        unique_code = f"VERIFY_{uuid.uuid4().hex[:6].upper()}"
        insert_res = mcp_server.insert("courses", {"code": unique_code, "title": "Verification Course", "credits": 3})
        agg_res = mcp_server.aggregate("enrollments", metric="avg", column="score")
        valid_success = search_res["count"] == 2 and insert_res["inserted_id"] is not None and len(agg_res["rows"]) > 0
        check("4. Valid Tool Calls", valid_success, "(search, insert, aggregate all returned valid payloads)")
    except Exception as e:
        check("4. Valid Tool Calls", False, f"(Raised error: {e})")

    # 5. Check invalid tool calls (Error handling & Safety)
    try:
        mcp_server.search("fake_table_123")
        check("5. Invalid Table Error Handling", False, "(Failed to reject unknown table)")
    except ValidationError:
        check("5. Invalid Table Error Handling", True, "(Safely rejected unknown table with ValidationError)")
    except Exception as e:
        check("5. Invalid Table Error Handling", True, f"(Safely rejected with error: {type(e).__name__})")

    try:
        mcp_server.insert("students", {})
        check("6. Empty Insert Error Handling", False, "(Failed to reject empty insert payload)")
    except ValidationError:
        check("6. Empty Insert Error Handling", True, "(Safely rejected empty payload)")
    except Exception as e:
        check("6. Empty Insert Error Handling", True, f"(Safely rejected with error: {type(e).__name__})")

    # 7. Check reading schema resources
    try:
        full_schema = json.loads(mcp_server.database_schema())
        tbl_schema = json.loads(mcp_server.table_schema("students"))
        schema_success = "tables" in full_schema and tbl_schema["table"] == "students"
        check("7. Schema Resource Reads", schema_success, "(Read schema://database and schema://table/students)")
    except Exception as e:
        check("7. Schema Resource Reads", False, f"(Error: {e})")

    print("\n======================================================")
    print(f"Summary: {passed}/{total} checks passed.")
    print("======================================================")
    if passed != total:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(verify())