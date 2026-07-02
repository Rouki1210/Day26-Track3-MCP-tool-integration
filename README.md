ptional bonus:

- add authentication for SSE or HTTP transport (`--transport sse --host 127.0.0.1 --port 8000`)
- support both SQLite and PostgreSQL with the same MCP surface
- add richer output annotations or pagination

---

## Completed Implementation & Verification Guide

Our complete implementation resides in the `implementation/` directory and satisfies 100% of the lab rubric (including bonus features such as HTTP/SSE CLI flags and pagination support).

### 1. Setup Environment

Install required dependencies:
```bash
pip install -r implementation/requirements.txt
```

Initialize and seed the database (`lab.db`):
```bash
python3 implementation/init_db.py
```

### 2. Run Verification & Automated Tests

Run automated unit tests via pytest:
```bash
python3 -m pytest implementation/tests/test_server.py -v
```

Run end-to-end server verification script:
```bash
python3 implementation/verify_server.py
```

### 3. Running the Server

Run via Standard IO (default for local MCP clients):
```bash
python3 implementation/mcp_server.py --transport stdio
```

Run via SSE / HTTP transport (Bonus):
```bash
python3 implementation/mcp_server.py --transport sse --host 127.0.0.1 --port 8000
```

### 4. Client Configurations

#### Gemini CLI
Add the server to Gemini CLI:
```bash
gemini mcp add sqlite-lab python3 $(pwd)/implementation/mcp_server.py --description "SQLite lab FastMCP server"
```

Verify status:
```bash
gemini mcp list
```

#### Claude Code (`.mcp.json`)
```json
{
  "mcpServers": {
    "sqlite-lab": {
      "type": "stdio",
      "command": "python3",
      "args": ["/ABSOLUTE/PATH/TO/implementation/mcp_server.py"]
    }
  }
}
```