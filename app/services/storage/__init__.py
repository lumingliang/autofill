"""
存储服务模块
提供文件上传、存储、压缩、裁剪等功能
"""
from .file_service import FileService, file_service, save_upload_file, save_upload_image

__all__ = [
    "FileService",
    "file_service",
    "save_upload_file",
    "save_upload_image",
]