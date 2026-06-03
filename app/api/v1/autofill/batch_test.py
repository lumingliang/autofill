"""
批量测试任务管理接口

参考 depts.py 简洁风格：
- 直接在路由函数中调用 Service 层
- 不使用 API 类包装
- 认证由中间件统一处理
- 租户过滤由 Repository 层自动处理
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query, UploadFile, File, Form
from fastapi.responses import StreamingResponse

from app.schemas.base import Fail, Success, SuccessExtra
from app.schemas.batch_test import BatchTestListQuery, BatchTestResultQuery
from app.services.autofill.batch_test_service import batch_test_service

router = APIRouter()


@router.post("/tasks/preview", summary="文件预览")
async def preview_file(
    file: UploadFile = File(..., description="Excel/CSV文件"),
):
    """
    预览文件内容

    导入前先预览文件内容，验证文件格式
    返回前5行样本数据，检查是否包含必需的 query 列
    """
    try:
        result = await batch_test_service.preview_file(file)
        return Success(data=result)
    except Exception as e:
        return Fail(code=400, msg=str(e))


@router.post("/tasks/import", summary="导入文件创建任务")
async def import_file(
    file: UploadFile = File(..., description="Excel/CSV文件"),
    dify_agent_id: int = Form(..., description="Dify Agent ID"),
    task_name: Optional[str] = Form(None, description="任务名称（可选）"),
    remark: str = Form("", description="备注"),
):
    """
    导入文件创建批量测试任务

    处理流程：
    1. 解析上传的 Excel/CSV 文件
    2. 验证必须包含 `query` 列
    3. 生成任务名称（如果用户未填写）：`{文件名}_{时间戳}`
    4. 创建批量测试任务记录（version_no = 1）
    5. 创建 SeekDB 集合，写入初始数据（status=0）
    6. 发送 Kafka 消息触发测试执行
    7. 返回任务信息
    """
    try:
        result = await batch_test_service.import_file(
            file=file,
            dify_agent_id=dify_agent_id,
            task_name=task_name,
            remark=remark
        )
        return Success(data=result)
    except Exception as e:
        return Fail(code=400, msg=str(e))


@router.get("/tasks/list", summary="获取任务列表")
async def list_tasks(
    query: BatchTestListQuery = Depends(),
):
    """获取批量测试任务列表"""
    try:
        total, items = await batch_test_service.list_tasks(
            keyword=query.keyword,
            page=query.page,
            page_size=query.page_size
        )
        return SuccessExtra(
            data=items,
            total=total,
            page=query.page,
            page_size=query.page_size
        )
    except Exception as e:
        return Fail(code=400, msg=str(e))


@router.get("/tasks/{task_id}", summary="获取任务详情")
async def get_task_detail(
    task_id: int,
):
    """获取批量测试任务详情"""
    try:
        result = await batch_test_service.get_task_detail(task_id)
        return Success(data=result)
    except Exception as e:
        return Fail(code=404, msg=str(e))


@router.post("/tasks/{task_id}/stop", summary="停止执行任务")
async def stop_task(
    task_id: int,
):
    """
    停止执行任务

    处理流程：
    1. 检查任务状态，只有执行中（status=1）的任务可以停止
    2. 更新任务状态为已停止（status=4）
    3. 保留已执行的结果
    """
    try:
        result = await batch_test_service.stop_task(task_id)
        return Success(data=result)
    except Exception as e:
        return Fail(code=400, msg=str(e))


@router.delete("/tasks/{task_id}", summary="删除任务")
async def delete_task(
    task_id: int,
):
    """
    删除任务

    处理流程：
    1. 删除所有版本的 SeekDB 集合
    2. 删除任务记录

    注意：执行中的任务（status=1）不允许删除
    """
    try:
        await batch_test_service.delete_task(task_id)
        return Success(msg="删除成功")
    except Exception as e:
        return Fail(code=400, msg=str(e))


@router.post("/tasks/{task_id}/retry", summary="重新执行任务")
async def retry_task(
    task_id: int,
    user_id: int = 0,
):
    """
    重新执行任务（创建新任务，复制原任务数据）

    处理流程：
    1. 复制原任务的数据到新的 SeekDB 集合
    2. 创建新任务记录
    3. 发送 Kafka 消息触发新任务的测试执行
    """
    try:
        result = await batch_test_service.retry_task(task_id, user_id)
        return Success(data=result)
    except Exception as e:
        return Fail(code=400, msg=str(e))


@router.get("/tasks/{task_id}/results", summary="获取测试结果列表")
async def get_results(
    task_id: int,
    query: BatchTestResultQuery = Depends(),
):
    """
    获取测试结果列表

    从 SeekDB 查询当前版本的数据
    支持按状态筛选
    """
    try:
        result = await batch_test_service.get_results(
            task_id=task_id,
            status=query.status,
            page=query.page,
            page_size=query.page_size
        )
        return SuccessExtra(
            data=result["items"],
            total=result["total"],
            page=query.page,
            page_size=query.page_size
        )
    except Exception as e:
        return Fail(code=400, msg=str(e))


@router.get("/tasks/{task_id}/export", summary="导出测试结果")
async def export_results(
    task_id: int,
):
    """
    导出测试结果

    导出CSV格式：
    - 包含原始所有列
    - 新增列：status, execution_time_ms, error_msg, started_at, completed_at
    - 将 Dify 返回的字段作为独立列导出
    - 只包含当前版本的数据
    """
    try:
        output = await batch_test_service.export_results(task_id)

        # 获取任务信息用于文件名
        task = await batch_test_service.get_task_detail(task_id)
        file_name = f"{task['task_name']}_v{task['version_no']}_results.csv"

        # 对文件名进行URL编码以支持中文
        from urllib.parse import quote
        encoded_filename = quote(file_name)

        return StreamingResponse(
            output,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
            }
        )
    except Exception as e:
        return Fail(code=400, msg=str(e))
