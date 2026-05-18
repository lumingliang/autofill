"""
测试填单服务层
封装参数并通过 HTTP 请求调用 step_llm_fill_handler 接口
"""
import os
import time
import uuid
from typing import Any, Dict, List, Optional

import httpx
from fastapi.exceptions import HTTPException

from app.log import logger
from app.models.autofill import AppManagement, FillPage, FieldGroupConfig, FieldSpec
from app.services.llm.llm_config_service import llm_config_service


class TestFillService:
    """测试填单服务"""

    @staticmethod
    async def chat_session(
        tenant_id: int,
        app_name: str,
        session_id: Optional[str],
        system_prompt: Optional[str],
        message: str,
        clear_history: bool = False
    ) -> Dict[str, Any]:
        """
        聊天会话处理 - 支持多轮对话（保持原有逻辑）
        """
        from app.services.llm.llm_proxy_service import llm_proxy_service
        from datetime import datetime

        if not message:
            raise HTTPException(status_code=400, detail="message is required")

        # 使用默认系统提示词
        if not system_prompt:
            system_prompt = """你是一个专业的客服对话生成专家。请根据用户的要求生成真实的客服与用户的对话记录。

生成要求：
1. 对话格式：每轮对话包含"客服："和"用户："两部分
2. 对话内容要真实自然，符合实际客服场景
3. 用户问题要具体、有细节
4. 客服回复要专业、有帮助
5. 对话要有逻辑连贯性，前后呼应
6. 严格按照用户要求的轮数生成

输出格式示例：
客服：您好，欢迎咨询，请问有什么可以帮您？
用户：你好，我的车出了点问题。
客服：请问是什么车型？具体什么问题？
用户：比亚迪汉EV，突然无法启动了。
...

请根据用户的要求生成对话记录。"""

        # 生成新的session_id
        if not session_id or clear_history:
            session_id = f"chat_{uuid.uuid4().hex[:16]}"

        # 获取LLM配置
        config = await llm_config_service.get_default_config()

        if not config:
            raise HTTPException(status_code=500, detail="No LLM configuration found")

        try:
            start_time = time.time()

            result = await llm_proxy_service.process_request(
                query=message,
                system_prompt=system_prompt,
                config=config,
                method="plain"
            )

            elapsed_time = time.time() - start_time

            # plain 模式返回的数据结构
            # result 结构: {"success": ..., "data": {"raw_response": ..., "content": ...}, ...}
            data = result.get("data", {})
            assistant_content = data.get("raw_response", "")
            if not assistant_content:
                assistant_content = data.get("content", "") or data.get("response", "") or str(result)

            # 构建历史记录
            history = [
                {"role": "user", "content": message, "timestamp": datetime.now().isoformat()},
                {"role": "assistant", "content": assistant_content, "timestamp": datetime.now().isoformat()}
            ]

            return {
                "session_id": session_id,
                "message": assistant_content,
                "history": history,
                "model": config.litellm_params.get("model", "unknown"),
                "usage": {
                    "prompt_tokens": result.get("_meta", {}).get("prompt_tokens", 0),
                    "completion_tokens": result.get("_meta", {}).get("completion_tokens", 0)
                },
                "elapsed_time": elapsed_time
            }

        except Exception as e:
            logger.error(f"Chat session failed: {e}")
            raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")

    @staticmethod
    async def test_fill(
        tenant_id: int,
        app_id: int,
        page_id: int,
        group_id: int,
        field_ids: List[int],
        chat_record: str
    ) -> Dict[str, Any]:
        """
        测试填单功能
        根据应用ID、页面ID、字段组ID、字段ID列表和聊天记录进行填单
        1. 根据ID查询对应的名称
        2. 根据app_name+tenant_id查询api_key
        3. 构造参数，通过HTTP请求调用 step_llm_fill_handler 接口
        """
        if not app_id:
            raise HTTPException(status_code=400, detail="app_id is required")
        if not page_id:
            raise HTTPException(status_code=400, detail="page_id is required")
        if not group_id:
            raise HTTPException(status_code=400, detail="group_id is required")
        if not field_ids:
            raise HTTPException(status_code=400, detail="field_ids is required")
        if not chat_record:
            raise HTTPException(status_code=400, detail="chat_record is required")

        # 1. 查询应用信息
        app = await AppManagement.filter(
            id=app_id,
            tenant_id=tenant_id,
            is_active=True
        ).first()
        if not app:
            raise HTTPException(status_code=404, detail=f"App with id '{app_id}' not found")

        # 2. 查询页面信息
        page = await FillPage.filter(
            id=page_id,
            tenant_id=tenant_id,
            is_active=True
        ).first()
        if not page:
            raise HTTPException(status_code=404, detail=f"Page with id '{page_id}' not found")

        # 3. 查询字段组信息
        group = await FieldGroupConfig.filter(
            id=group_id,
            page_id=page_id,
            is_active=True
        ).first()
        if not group:
            raise HTTPException(status_code=404, detail=f"Field group with id '{group_id}' not found")

        # 4. 查询字段信息
        # 先验证这些字段是否确实属于该字段组（通过中间表关联）
        from app.models.autofill import FieldGroupFieldSpec
        relations = await FieldGroupFieldSpec.filter(
            field_group_id=group_id,
            field_spec_id__in=field_ids
        ).all()
        valid_field_ids = [r.field_spec_id for r in relations]

        if not valid_field_ids:
            raise HTTPException(status_code=404, detail="No valid fields found for this group")

        fields = await FieldSpec.filter(
            id__in=valid_field_ids,
            is_active=True
        ).all()
        if not fields:
            raise HTTPException(status_code=404, detail="Fields not found")

        field_names = [f.field_name for f in fields]

        # 5. 生成session_id
        session_id = f"test_{uuid.uuid4().hex[:12]}"

        # 6. 构造 group_fields 参数
        group_fields = {group.group_name: field_names}

        # 7. 构造请求参数（符合 step_llm_fill_handler 的接口格式）
        request_data = {
            "session_id": session_id,
            "page_name": page.page_name,
            "group_fields": group_fields,
            "query": chat_record,
            "method": None,
            "system_prompt": None,
            "include_reason": False,
            "memory_rounds": 0,
            "additional_data": None,
            "use_additional_data": False,
            "is_last": True
        }

        # 8. 调用 step_llm_fill_handler 接口
        # 使用内部HTTP请求访问public接口
        try:
            # 从环境变量获取端口，默认为 9999（与 run.py 一致）
            port = int(os.environ.get('APP_PORT', '9999'))
            base_url = f"http://localhost:{port}"
            url = f"{base_url}/api/autofill/llm/fill/step"

            # 构建请求头，使用API Key认证
            headers = {
                "Authorization": f"Bearer {app.api_key}",
                "Content-Type": "application/json"
            }

            start_time = time.time()

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=request_data,
                    headers=headers,
                    timeout=120.0
                )

            elapsed_time = time.time() - start_time

            if response.status_code != 200:
                error_detail = response.text
                logger.error(f"step_llm_fill_handler error: {error_detail}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"填单处理失败: {error_detail}"
                )

            result = response.json()

            # 添加额外信息到结果
            if result.get("code") == 200:
                data = result.get("data", {})
                data["elapsed_time"] = elapsed_time
                data["page_name"] = page.page_name
                return data
            else:
                raise HTTPException(
                    status_code=500,
                    detail=result.get("msg", "填单处理失败")
                )

        except httpx.RequestError as e:
            logger.error(f"HTTP request error: {e}")
            raise HTTPException(status_code=500, detail=f"请求填单服务失败: {str(e)}")
        except Exception as e:
            logger.error(f"Test fill error: {e}")
            raise HTTPException(status_code=500, detail=f"填单测试失败: {str(e)}")


# 创建服务实例
test_fill_service = TestFillService()
