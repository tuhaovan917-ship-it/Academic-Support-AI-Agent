from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.api import AgentService, AgentServiceRequest


def main() -> int:
    parser = argparse.ArgumentParser(description="Run API-ready HUIT AgentService contract.")
    parser.add_argument("query", nargs="?", help="User question")
    parser.add_argument("--student-id")
    parser.add_argument("--session-id")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--include-retrieval", action="store_true")
    parser.add_argument("--hide-tool-results", action="store_true")
    args = parser.parse_args()

    query = args.query or input("Bạn hỏi gì? ").strip()
    request = AgentServiceRequest(
        query=query,
        student_id=args.student_id,
        session_id=args.session_id,
        include_debug=args.debug,
        include_retrieval=args.include_retrieval,
        include_tool_results=not args.hide_tool_results,
    )
    response = AgentService().ask(request)
    print(json.dumps(response.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
