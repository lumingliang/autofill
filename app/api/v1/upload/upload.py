"""
文件上传 API - 使用文件管理服务
"""

from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile, Depends

from app.core.dependency import AuthControl
from app.log import logger
from app.models import User
from app.schemas.base import Success, Fail
from app.services.storage.file_service import FileService, file_service

router = APIRouter()

# 头像专用文件服务
avatar_service = FileService(
    upload_dir="./uploads/avatars",
    allowed_extensions={".jpg", ".jpeg", ".png", ".gif", ".webp"},
    max_file_size=5 * 1024 * 1024,  # 5MB
    url_prefix="/uploads/avatars",
)


@router.post("/avatar", summary="上传用户头像")
async def upload_avatar(
    file: UploadFile = File(..., description="头像图片文件"),
    user: User = Depends(AuthControl.is_authed),
):
    """
    用户头像上传接口
    - 支持格式: jpg, jpeg, png, gif, webp
    - 最大 5MB
    - 自动压缩至 800x800
    """
    try:
        # 保存并处理图片
        result = await avatar_service.save_image(
            file=file,
            prefix=f"user_{user.id}",
            max_dimension=800,  # 头像最大 800px
            quality=90,
        )

        # 更新用户头像
        user.avatar = result["url"]
        await user.save()

        logger.info(f"用户 {user.id} 上传了头像: {result['url']}")

        return Success(
            msg="头像上传成功",
            data={
                "url": result["url"],
                "filename": result["filename"],
                "width": result.get("width"),
                "height": result.get("height"),
                "size": result["size"],
            },
        )

    except ValueError as e:
        return Fail(msg=str(e))
    except Exception as e:
        logger.error(f"头像上传失败: {e}")
        return Fail(msg="头像上传失败，请稍后重试")


@router.post("/file", summary="通用文件上传")
async def upload_file(
    file: UploadFile = File(..., description="文件"),
    file_type: str = Form("file", description="文件类型: file, image, document"),
    user: User = Depends(AuthControl.is_authed),
):
    """
    通用文件上传接口
    - file_type: file(通用文件), image(图片), document(文档)
    - 图片会自动压缩
    """
    try:
        subdir = file_type if file_type in ("image", "document", "file") else "file"

        if file_type == "image":
            # 图片使用图片处理流程
            result = await file_service.save_image(
                file=file,
                subdir=subdir,
                prefix=f"user_{user.id}",
                max_dimension=2048,
            )
        else:
            # 其他文件直接保存
            result = await file_service.save_file(
                file=file,
                subdir=subdir,
                prefix=f"user_{user.id}",
            )

        logger.info(f"用户 {user.id} 上传了文件: {result['filename']}")

        return Success(
            msg="上传成功",
            data={
                "url": result["url"],
                "filename": result["filename"],
                "original_name": result["original_name"],
                "size": result["size"],
                "mimetype": result["mimetype"],
                "type": file_type,
                **({"width": result["width"], "height": result["height"]} if "width" in result else {}),
            },
        )

    except ValueError as e:
        return Fail(msg=str(e))
    except Exception as e:
        logger.error(f"文件上传失败: {e}")
        return Fail(msg="文件上传失败，请稍后重试")


@router.delete("/file", summary="删除文件")
async def delete_uploaded_file(
    file_path: str = Form(..., description="文件路径或 URL"),
    user: User = Depends(AuthControl.is_authed),
):
    """
    删除已上传的文件
    - 只能删除自己上传的文件
    """
    try:
        # 检查文件路径是否包含用户前缀（简单权限控制）
        expected_prefix = f"user_{user.id}"
        if expected_prefix not in file_path:
            return Fail(msg="只能删除自己上传的文件")

        # 从 URL 提取相对路径
        if "/uploads/" in file_path:
            relative_path = file_path.split("/uploads/")[-1]
        else:
            relative_path = file_path

        success = file_service.delete_file(relative_path)

        if success:
            logger.info(f"用户 {user.id} 删除了文件: {file_path}")
            return Success(msg="文件删除成功")
        else:
            return Fail(msg="文件不存在或删除失败")

    except Exception as e:
        logger.error(f"文件删除失败: {e}")
        return Fail(msg="文件删除失败")


@router.get("/file/info", summary="获取文件信息")
async def get_file_info(
    file_path: str,
    user: User = Depends(AuthControl.is_authed),
):
    """
    获取文件信息
    """
    try:
        # 从 URL 提取相对路径
        if "/uploads/" in file_path:
            relative_path = file_path.split("/uploads/")[-1]
        else:
            relative_path = file_path

        info = file_service.get_file_info(relative_path)

        if info:
            return Success(data=info)
        else:
            return Fail(msg="文件不存在")

    except Exception as e:
        logger.error(f"获取文件信息失败: {e}")
        return Fail(msg="获取文件信息失败")
