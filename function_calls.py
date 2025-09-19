import json
from dumpster_functions import FUNCTION_MAP

def execute_function_call(func_name, arguments):
    if func_name in FUNCTION_MAP:
        result = FUNCTION_MAP[func_name](**arguments)
        print(f"[Function call] {func_name} result: {result}")
        return result
    print(f"[Function call] Unknown function: {func_name}")
    return {"error": f"Unknown function: {func_name}"}

def create_function_call_response(func_id, func_name, result):
    return {
        "type": "FunctionCallResponse",
        "id": func_id,
        "name": func_name,
        "content": json.dumps(result),
    }
