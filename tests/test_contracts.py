import json

from agent.prompt import runtime_json_prompt
from agent.tool_registry import get_tool_schemas_for_prompt, get_tool_schemas_for_training
from scripts.generate_seed_data import build_seed_samples
from tools.schemas import CreateTaskRequest, GenerateCopyRequest


def test_registry_matches_create_task_request_fields() -> None:
    schema = next(item for item in get_tool_schemas_for_prompt() if item["function"]["name"] == "create_opt_task")
    fields = set(schema["function"]["parameters"]["properties"].keys())
    assert fields == set(CreateTaskRequest.model_fields.keys())


def test_registry_matches_generate_copy_request_fields() -> None:
    schema = next(item for item in get_tool_schemas_for_prompt() if item["function"]["name"] == "generate_ad_copy")
    fields = set(schema["function"]["parameters"]["properties"].keys())
    assert fields == set(GenerateCopyRequest.model_fields.keys())


def test_prompt_embeds_registry_schema() -> None:
    prompt = runtime_json_prompt(user_query="diagnose image", retrieved_rules=[], image_count=1)
    for tool in get_tool_schemas_for_prompt():
        assert tool["function"]["name"] in prompt


def test_generated_seed_data_uses_registry_tools() -> None:
    sample = build_seed_samples()[0]
    assert json.loads(sample["tools"]) == get_tool_schemas_for_training()
