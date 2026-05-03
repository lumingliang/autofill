"""
文件管理服务 - 使用 Python 标准库和 Pillow 实现
提供文件上传、存储、压缩、裁剪等功能
"""

import os
import uuid
import shutil
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Optional, BinaryIO, Tuple
from io import BytesIO

from PIL import Image, ImageOps
from fastapi import UploadFile

from app.settings.config import settings
import logging

logger = logging.getLogger(__name__)


class FileService:
    """文件管理服务"""

    # 默认配置
    DEFAULT_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
    DEFAULT_MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    DEFAULT_IMAGE_QUALITY = 85
    DEFAULT_MAX_IMAGE_DIMENSION = 2048  # 最大边长

    def __init__(
        self,
        upload_dir: Optional[str] = None,
        allowed_extensions: Optional[set] = None,
        max_file_size: Optional[int] = None,
        url_prefix: Optional[str] = None,
    ):
        self.upload_dir = Path(upload_dir or settings.UPLOAD_DIR)
        self.allowed_extensions = allowed_extensions or self.DEFAULT_ALLOWED_EXTENSIONS
        self.max_file_size = max_file_size or self.DEFAULT_MAX_FILE_SIZE
        self.url_prefix = url_prefix or settings.FILE_URL_PREFIX

        # 确保上传目录存在
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def _get_file_extension(self, filename: str) -> str:
        """获取文件扩展名（小写）"""
        return Path(filename).suffix.lower()

    def _is_allowed_file(self, filename: str) -> bool:
        """检查文件类型是否允许"""
        ext = self._get_file_extension(filename)
        return ext in self.allowed_extensions

    def _generate_filename(self, original_filename: str, prefix: str = "") -> str:
        """生成新的文件名"""
        ext = self._get_file_extension(original_filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:8]

        if prefix:
            return f"{prefix}_{timestamp}_{unique_id}{ext}"
        return f"{timestamp}_{unique_id}{ext}"

    def _get_save_path(self, filename: str, subdir: Optional[str] = None) -> Path:
        """获取文件保存路径"""
        if subdir:
            save_dir = self.upload_dir / subdir
        else:
            # 按日期组织文件
            today = datetime.now().strftime("%Y/%m/%d")
            save_dir = self.upload_dir / today

        save_dir.mkdir(parents=True, exist_ok=True)
        return save_dir / filename

    def _get_file_url(self, relative_path: str) -> str:
        """获取文件访问 URL"""
        return f"{self.url_prefix}/{relative_path}"

    async def save_file(
        self,
        file: UploadFile,
        subdir: Optional[str] = None,
        prefix: str = "",
        custom_filename: Optional[str] = None,
    ) -> dict:
        """
        保存上传的文件

        Args:
            file: FastAPI UploadFile 对象
            subdir: 子目录名称
            prefix: 文件名前缀
            custom_filename: 自定义文件名（不含扩展名）

        Returns:
            dict: 包含文件信息的字典
        """
        # 检查文件类型
        if not self._is_allowed_file(file.filename):
            allowed = ", ".join(self.allowed_extensions)
            raise ValueError(f"不支持的文件类型，允许的类型: {allowed}")

        # 读取文件内容
        content = await file.read()

        # 检查文件大小
        if len(content) > self.max_file_size:
            max_mb = self.max_file_size / 1024 / 1024
            raise ValueError(f"文件大小超过限制，最大允许 {max_mb}MB")

        # 生成文件名
        if custom_filename:
            ext = self._get_file_extension(file.filename)
            filename = f"{custom_filename}{ext}"
        else:
            filename = self._generate_filename(file.filename, prefix)

        # 获取保存路径
        file_path = self._get_save_path(filename, subdir)

        # 保存文件
        with open(file_path, "wb") as f:
            f.write(content)

        # 计算相对路径用于 URL
        relative_path = file_path.relative_to(self.upload_dir)

        logger.info(f"文件已保存: {file_path}")

        return {
            "filename": filename,
            "original_name": file.filename,
            "path": str(file_path),
            "url": self._get_file_url(str(relative_path).replace("\\", "/")),
            "size": len(content),
            "mimetype": file.content_type or mimetypes.guess_type(filename)[0],
        }

    async def save_image(
        self,
        file: UploadFile,
        subdir: Optional[str] = None,
        prefix: str = "",
        max_dimension: Optional[int] = None,
        quality: Optional[int] = None,
        convert_format: Optional[str] = None,
    ) -> dict:
        """
        保存图片文件，支持自动压缩和格式转换

        Args:
            file: FastAPI UploadFile 对象
            subdir: 子目录名称
            prefix: 文件名前缀
            max_dimension: 最大边长，超过则等比例压缩
            quality: 图片质量（1-100）
            convert_format: 转换格式（如 'JPEG', 'PNG', 'WEBP'）

        Returns:
            dict: 包含图片信息的字典
        """
        # 先保存原始文件
        result = await self.save_file(file, subdir, prefix)
        file_path = Path(result["path"])

        try:
            # 打开图片进行处理
            with Image.open(file_path) as img:
                # 处理 EXIF 旋转信息
                img = ImageOps.exif_transpose(img)

                # 转换为 RGB（处理透明通道）
                if img.mode in ("RGBA", "P"):
                    if convert_format == "JPEG":
                        img = img.convert("RGB")

                # 调整尺寸
                max_dim = max_dimension or self.DEFAULT_MAX_IMAGE_DIMENSION
                if max(img.size) > max_dim:
                    ratio = max_dim / max(img.size)
                    new_size = tuple(int(dim * ratio) for dim in img.size)
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                    logger.info(f"图片已压缩: {img.size}")

                # 确定输出格式
                output_format = convert_format
                if not output_format:
                    ext = file_path.suffix.lower()
                    format_map = {
                        ".jpg": "JPEG",
                        ".jpeg": "JPEG",
                        ".png": "PNG",
                        ".gif": "GIF",
                        ".webp": "WEBP",
                        ".bmp": "BMP",
                    }
                    output_format = format_map.get(ext, "JPEG")

                # 确定输出路径
                if convert_format:
                    new_ext = f".{convert_format.lower()}"
                    new_filename = file_path.stem + new_ext
                    new_path = file_path.with_name(new_filename)
                else:
                    new_path = file_path

                # 保存处理后的图片
                save_kwargs = {}
                if output_format in ("JPEG", "WEBP"):
                    save_kwargs["quality"] = quality or self.DEFAULT_IMAGE_QUALITY
                    save_kwargs["optimize"] = True
                elif output_format == "PNG":
                    save_kwargs["optimize"] = True

                img.save(new_path, format=output_format, **save_kwargs)

                # 如果转换了格式，删除原文件
                if convert_format and new_path != file_path:
                    file_path.unlink()
                    file_path = new_path
                    result["filename"] = new_filename

                # 更新结果信息
                result["path"] = str(file_path)
                result["size"] = file_path.stat().st_size
                result["width"] = img.width
                result["height"] = img.height
                result["format"] = output_format

                # 更新 URL
                relative_path = file_path.relative_to(self.upload_dir)
                result["url"] = self._get_file_url(str(relative_path).replace("\\", "/"))

                logger.info(f"图片已处理并保存: {file_path}")

        except Exception as e:
            logger.error(f"图片处理失败: {e}")
            # 图片处理失败但不删除已保存的文件

        return result

    async def crop_and_save_image(
        self,
        file: UploadFile,
        crop_box: Tuple[int, int, int, int],  # (left, top, right, bottom)
        subdir: Optional[str] = None,
        prefix: str = "",
        output_size: Optional[Tuple[int, int]] = None,
    ) -> dict:
        """
        裁剪图片并保存

        Args:
            file: FastAPI UploadFile 对象
            crop_box: 裁剪框坐标 (left, top, right, bottom)
            subdir: 子目录名称
            prefix: 文件名前缀
            output_size: 输出尺寸 (width, height)

        Returns:
            dict: 包含图片信息的字典
        """
        # 先保存原始文件
        result = await self.save_file(file, subdir, prefix)
        file_path = Path(result["path"])

        try:
            with Image.open(file_path) as img:
                # 处理 EXIF 旋转
                img = ImageOps.exif_transpose(img)

                # 裁剪
                cropped = img.crop(crop_box)

                # 调整输出尺寸
                if output_size:
                    cropped = cropped.resize(output_size, Image.Resampling.LANCZOS)

                # 保存
                save_kwargs = {}
                ext = file_path.suffix.lower()
                if ext in (".jpg", ".jpeg"):
                    save_kwargs["quality"] = self.DEFAULT_IMAGE_QUALITY
                    save_kwargs["optimize"] = True

                cropped.save(file_path, **save_kwargs)

                # 更新结果
                result["size"] = file_path.stat().st_size
                result["width"] = cropped.width
                result["height"] = cropped.height

                logger.info(f"图片已裁剪并保存: {file_path}")

        except Exception as e:
            logger.error(f"图片裁剪失败: {e}")
            raise

        return result

    def delete_file(self, file_path: str) -> bool:
        """
        删除文件

        Args:
            file_path: 文件路径（绝对路径或相对 upload_dir 的路径）

        Returns:
            bool: 是否删除成功
        """
        try:
            path = Path(file_path)
            if not path.is_absolute():
                path = self.upload_dir / path

            if path.exists():
                path.unlink()
                logger.info(f"文件已删除: {path}")
                return True
            else:
                logger.warning(f"文件不存在: {path}")
                return False

        except Exception as e:
            logger.error(f"删除文件失败: {e}")
            return False

    def get_file_info(self, file_path: str) -> Optional[dict]:
        """
        获取文件信息

        Args:
            file_path: 文件路径

        Returns:
            dict: 文件信息，文件不存在返回 None
        """
        try:
            path = Path(file_path)
            if not path.is_absolute():
                path = self.upload_dir / path

            if not path.exists():
                return None

            stat = path.stat()
            relative_path = path.relative_to(self.upload_dir)

            info = {
                "filename": path.name,
                "path": str(path),
                "url": self._get_file_url(str(relative_path).replace("\\", "/")),
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            }

            # 如果是图片，获取图片信息
            if path.suffix.lower() in self.DEFAULT_ALLOWED_EXTENSIONS:
                try:
                    with Image.open(path) as img:
                        info["width"] = img.width
                        info["height"] = img.height
                        info["format"] = img.format
                        info["mode"] = img.mode
                except Exception:
                    pass

            return info

        except Exception as e:
            logger.error(f"获取文件信息失败: {e}")
            return None


# 创建默认实例
file_service = FileService()


# 便捷函数
async def save_upload_file(
    file: UploadFile,
    subdir: Optional[str] = None,
    prefix: str = "",
) -> dict:
    """保存上传文件"""
    return await file_service.save_file(file, subdir, prefix)


async def save_upload_image(
    file: UploadFile,
    subdir: Optional[str] = None,
    prefix: str = "",
    max_dimension: Optional[int] = None,
) -> dict:
    """保存上传图片（自动压缩）"""
    return await file_service.save_image(file, subdir, prefix, max_dimension)
