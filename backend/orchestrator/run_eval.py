import asyncio
import sys
import json
from datetime import datetime
from pathlib import Path

# Add project root to path to ensure imports work whether run as script or module
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.orchestrator.services.eval_runner import EvaluationRunner
from backend.orchestrator.services.conversation_service import ConversationService
from backend.orchestrator.eval_suites.basic_suite import BASIC_SUITE

class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)

async def main():
    print("Initializing Evaluation Runner...")
    # Initialize service - this will load agents/dependencies
    service = ConversationService()
    runner = EvaluationRunner(service)

    cases = BASIC_SUITE
    print(f"Running {len(cases)} test cases from BASIC_SUITE...")

    results = []
    for case in cases:
        print(f"  Running case: {case.id} ({case.eval_type})...", end="", flush=True)
        try:
            res = await runner.run_case(case)
            results.append(res)
            status = "PASS" if res.passed else "FAIL"
            print(f" {status} (Score: {res.score:.2f})")
            if not res.passed:
                print(f"    Details: {res.details}")
        except Exception as e:
            print(f" CRASH: {e}")
            import traceback
            traceback.print_exc()

    passed = sum(1 for r in results if r.passed)
    total = len(results)
    
    print("-" * 40)
    print(f"Evaluation Complete: {passed}/{total} passed.")
    print("-" * 40)

    output_file = "eval_results.json"
    with open(output_file, "w") as f:
        json.dump([r.dict() for r in results], f, indent=2, cls=DateTimeEncoder)
    print(f"Detailed results saved to {output_file}")

if __name__ == "__main__":
    asyncio.run(main())

