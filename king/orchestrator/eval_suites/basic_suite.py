from services.eval_contracts import EvalCase, EvalExpectation
from services.contracts import IntentType

BASIC_SUITE = [
    # 1. Intent Test: Direct Agent Match
    EvalCase(
        id="intent_code_gen",
        eval_type="intent",
        input_message="Generate a Python script to calculate Fibonacci sequence.",
        expectation=EvalExpectation(
            expected_intent_type=IntentType.GENERATE_CODE,
        ),
    ),
    
    # 2. Execution Test: Simple Code Gen
    EvalCase(
        id="execution_success_code",
        eval_type="execution",
        input_message="Write a python function to add two numbers.",
        expectation=EvalExpectation(
            must_succeed=True,
        ),
    ),

    # 3. Plan Test: Explicit planning request (likely to trigger fallback if no agent matches perfectly)
    # This might fail if the planner placeholder doesn't produce steps, but we want to test the harness.
    EvalCase(
        id="plan_fallback_check",
        eval_type="intent",
        input_message="Orchestrate a complex deployment.",
        expectation=EvalExpectation(
            expected_intent_type=IntentType.PLAN, # Expect fallback to plan
        ),
    ),
]






