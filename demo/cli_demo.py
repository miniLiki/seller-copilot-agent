from __future__ import annotations

import argparse
import json
from pathlib import Path

from agent.planner import get_runtime_summary, load_runtime_config, run_agent


def main() -> None:
    parser = argparse.ArgumentParser(description="Seller Copilot CLI demo")
    parser.add_argument("--image", required=True, help="Path to the product image")
    parser.add_argument("--product-id", required=True, help="Product ID used by the tool service")
    parser.add_argument("--query", required=True, help="User query to execute")
    parser.add_argument("--config", default="configs/runtime.yaml", help="Runtime config path")
    parser.add_argument("--save-trace", dest="save_trace", action="store_true", help="Persist run artifacts")
    parser.add_argument("--no-save-trace", dest="save_trace", action="store_false", help="Skip trace persistence")
    parser.set_defaults(save_trace=None)
    args = parser.parse_args()

    runtime_config = load_runtime_config(Path(args.config))
    trace = run_agent(
        image_path=Path(args.image),
        product_id=args.product_id,
        user_query=args.query,
        config_path=Path(args.config),
        save_trace=args.save_trace,
    )

    print("=" * 80)
    print("Runtime Config")
    print(json.dumps(get_runtime_summary(runtime_config), ensure_ascii=False, indent=2))
    print("\nUser Query")
    print(args.query)
    print("\nRetrieved Rules")
    print(json.dumps(trace.retrieval_results, ensure_ascii=False, indent=2))
    print("\nModel Output")
    print(trace.raw_model_output)
    print("\nTool Calls")
    tool_calls = trace.parsed_output.get("tool_calls", []) if trace.parsed_output else []
    print(json.dumps(tool_calls, ensure_ascii=False, indent=2))
    print("\nTool Results")
    print(json.dumps(trace.tool_results, ensure_ascii=False, indent=2))
    print("\nFinal Response")
    print(trace.final_response)
    if trace.errors:
        print("\nErrors")
        print(json.dumps(trace.errors, ensure_ascii=False, indent=2))
    print("=" * 80)


if __name__ == "__main__":
    main()
