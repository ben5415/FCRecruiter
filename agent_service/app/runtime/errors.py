class AgentRuntimeError(Exception):
    code = "agent_runtime_error"


class DuplicateToolError(AgentRuntimeError):
    code = "duplicate_tool"


class InvalidToolDefinitionError(AgentRuntimeError):
    code = "invalid_tool_definition"


class ModelResponseError(AgentRuntimeError):
    code = "invalid_model_response"
