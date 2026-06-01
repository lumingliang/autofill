"""
虚拟 Dify 服务器

用于测试 Agent 转发功能
"""
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import json
import time

app = FastAPI(title="Mock Dify Server")


class ChatRequest(BaseModel):
    query: str
    inputs: Optional[dict] = {}
    response_mode: str = "blocking"
    conversation_id: Optional[str] = None
    user: Optional[str] = None


@app.post("/v1/chat-messages")
async def chat_messages(
    request: ChatRequest,
    authorization: str = Header(...)
):
    """
    模拟 Dify 聊天接口
    """
    # 验证 API Key
    api_key = authorization.replace("Bearer ", "").strip()
    if not api_key.startswith("sk-"):
        raise HTTPException(status_code=401, detail="Invalid API key")

    print(f"[Mock Dify] Received request:")
    print(f"  - API Key: {api_key[:10]}...")
    print(f"  - Query: {request.query}")
    print(f"  - Response Mode: {request.response_mode}")
    print(f"  - Conversation ID: {request.conversation_id}")
    print(f"  - User: {request.user}")
    print(f"  - Inputs: {request.inputs}")

    if request.response_mode == "streaming":
        return StreamingResponse(
            stream_response(request),
            media_type="text/event-stream"
        )
    else:
        return {
            "message_id": f"msg-{int(time.time() * 1000)}",
            "conversation_id": request.conversation_id or f"conv-{int(time.time() * 1000)}",
            "answer": f"这是虚拟 Dify 的回复：你发送了 '{request.query}'",
            "created_at": int(time.time()),
            "metadata": {
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30
                }
            }
        }


async def stream_response(request: ChatRequest):
    """流式响应生成器"""
    conversation_id = request.conversation_id or f"conv-{int(time.time() * 1000)}"
    message_id = f"msg-{int(time.time() * 1000)}"

    # 发送开始事件
    yield f"data: {json.dumps({'event': 'message_start', 'conversation_id': conversation_id, 'message_id': message_id})}\n\n"

    # 模拟分块返回
    answer = f"这是虚拟 Dify 的流式回复：你发送了 '{request.query}'"
    chunks = answer.split(" ")

    for i, chunk in enumerate(chunks):
        yield f"data: {json.dumps({'event': 'message', 'conversation_id': conversation_id, 'message_id': message_id, 'answer': chunk + ' '})}\n\n"
        time.sleep(0.1)

    # 发送结束事件
    yield f"data: {json.dumps({'event': 'message_end', 'conversation_id': conversation_id, 'message_id': message_id})}\n\n"


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok", "service": "mock-dify"}


if __name__ == "__main__":
    import uvicorn
    print("启动虚拟 Dify 服务器...")
    print("访问地址: http://localhost:9998")
    print("聊天接口: POST http://localhost:9998/v1/chat-messages")
    uvicorn.run(app, host="0.0.0.0", port=9998)
