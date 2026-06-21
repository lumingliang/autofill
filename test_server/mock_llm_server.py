"""
Mock LLM server for testing the Agent refactor end-to-end.

Provides an OpenAI-compatible /v1/chat/completions endpoint that returns
canned responses. The server is stateless: it decides whether to emit a tool
call or a final answer by inspecting whether tool-result messages are already
present in the conversation history.
"""
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse

app = FastAPI(title="Mock LLM Server for Agent Testing")


def _build_tool_call_response(
    request_id: str,
    model: str,
    tool_calls: List[Dict[str, Any]],
    content: str = "",
) -> Dict[str, Any]:
    return {
        "id": f"chatcmpl-{request_id}",
        "object": "chat.completion",
        "created": int(datetime.now().timestamp()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content,
                    "tool_calls": tool_calls,
                },
                "finish_reason": "tool_calls",
            }
        ],
        "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
    }


def _build_text_response(
    request_id: str,
    model: str,
    content: str,
) -> Dict[str, Any]:
    return {
        "id": f"chatcmpl-{request_id}",
        "object": "chat.completion",
        "created": int(datetime.now().timestamp()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
    }


def _build_stream_chunk(
    request_id: str,
    model: str,
    content: str = "",
    tool_calls: List[Dict[str, Any]] | None = None,
    finish_reason: str | None = None,
) -> str:
    delta: Dict[str, Any] = {"role": "assistant"}
    if content:
        delta["content"] = content
    if tool_calls:
        delta["tool_calls"] = tool_calls
    chunk = {
        "id": f"chatcmpl-{request_id}",
        "object": "chat.completion.chunk",
        "created": int(datetime.now().timestamp()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": delta,
                "finish_reason": finish_reason,
            }
        ],
    }
    return f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    model = body.get("model", "mock-model")
    messages = body.get("messages", [])
    tools = body.get("tools", [])
    stream = body.get("stream", False)
    request_id = str(uuid.uuid4())[:8]

    # State decision: if we already see tool results, this is the follow-up turn.
    has_tool_results = any(m.get("role") == "tool" for m in messages)
    request_number = 1 if has_tool_results else 0

    print(f"\n[MockLLM] Request #{request_number} ({request_id}) model={model} stream={stream}")
    print(f"[MockLLM] Tools available: {[t.get('function', {}).get('name') for t in tools]}")
    print(f"[MockLLM] Messages roles: {[m.get('role') for m in messages]}")
    if messages:
        last = messages[-1]
        preview = str(last.get("content", ""))[:300].replace("\n", " ")
        print(f"[MockLLM] Last message preview: {preview}")

    if not has_tool_results and tools:
        # First turn -> ask to read a file
        tool_name = "Read"
        tool_args = {
            "file_path": "/Users/lu/code/code/py/autofill/app/services/agent/agent_loop.py",
            "limit": 5,
        }
        tool_calls = [
            {
                "id": f"call_{request_id}_read",
                "type": "function",
                "function": {"name": tool_name, "arguments": json.dumps(tool_args)},
            }
        ]
        print(f"[MockLLM] -> tool_calls: {tool_name}({tool_args})")
        if stream:
            chunks = [
                _build_stream_chunk(request_id, model, tool_calls=tool_calls),
                _build_stream_chunk(request_id, model, finish_reason="tool_calls"),
                "data: [DONE]\n\n",
            ]
            return StreamingResponse(iter(chunks), media_type="text/event-stream")
        return JSONResponse(_build_tool_call_response(request_id, model, tool_calls))

    # Follow-up turn -> final response
    final_content = "我已看到工具返回结果，现在给出最终回答。"
    print(f"[MockLLM] -> final content: {final_content}")
    if stream:
        chunks = [
            _build_stream_chunk(request_id, model, content=final_content),
            _build_stream_chunk(request_id, model, finish_reason="stop"),
            "data: [DONE]\n\n",
        ]
        return StreamingResponse(iter(chunks), media_type="text/event-stream")
    return JSONResponse(_build_text_response(request_id, model, final_content))


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    print("Starting Mock LLM server on http://127.0.0.1:9998")
    uvicorn.run(app, host="127.0.0.1", port=9998, log_level="info")
