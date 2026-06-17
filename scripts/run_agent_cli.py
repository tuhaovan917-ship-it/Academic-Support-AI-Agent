from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agents import run_agent


def main() -> int:
    parser = argparse.ArgumentParser(description="Run HUIT academic agent CLI.")
    parser.add_argument("query", nargs="?", help="User question")
    parser.add_argument("--student-id")
    parser.add_argument("--session-id", default="cli")
    parser.add_argument("--json", action="store_true", help="Print full response JSON")
    args = parser.parse_args()

    query = args.query or input("Bạn hỏi gì? ").strip()
    response = run_agent(query, student_id=args.student_id, session_id=args.session_id)
    if args.json:
        print(json.dumps(response.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(response.answer)
        if response.citations:
            print("\nTrích dẫn:")
            for citation in response.citations:
                print(f"- {citation}")
        if response.llm:
            print(f"\nLLM: {response.llm.get('provider')} (fallback={response.llm.get('fallback_used')})")
        if response.planner:
            planner_mode = response.planner.get("mode")
            planner_provider = response.planner.get("provider")
            planner_route = response.planner.get("llm_route") or response.planner.get("rule_route")
            suffix = f", provider={planner_provider}" if planner_provider else ""
            print(f"Planner: {planner_mode}, route={planner_route}{suffix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
