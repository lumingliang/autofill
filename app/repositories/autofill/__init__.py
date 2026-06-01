"""
Autofill 模块 Repository 层
"""
from .app_management_repository import AppManagementRepository, app_management_repository
from .dify_agent_repository import DifyAgentRepository, dify_agent_repository
from .fill_data_record_repository import FillDataRecordRepository, fill_data_record_repository
from .system_prompt_repository import SystemPromptRepository, system_prompt_repository

__all__ = [
    "AppManagementRepository",
    "app_management_repository",
    "DifyAgentRepository",
    "dify_agent_repository",
    "FillDataRecordRepository",
    "fill_data_record_repository",
    "SystemPromptRepository",
    "system_prompt_repository",
]
