"""
动作指纹与无效循环检测
"""
from difflib import SequenceMatcher
from typing import List, Optional, Tuple

from app.services.agent.models import Fingerprint, LoopDetectionConfig


def _fp_key(fp: dict) -> str:
    """指纹精确重复判定键"""
    return f"{fp.get('agent_id')}:{fp.get('call_type')}:{fp.get('name')}:{fp.get('args_hash')}"


def _similarity(a: dict, b: dict) -> float:
    """计算两个指纹的相似度"""
    if _fp_key(a) == _fp_key(b):
        return 1.0
    preview_a = str(a.get("args_preview", ""))
    preview_b = str(b.get("args_preview", ""))
    if not preview_a and not preview_b:
        return 1.0
    return SequenceMatcher(None, preview_a, preview_b).ratio()


def detect_loop(window: List[dict], config: LoopDetectionConfig) -> Tuple[bool, Optional[str]]:
    """检测无效循环

    Returns:
        (是否触发熔断, 原因)
    """
    if not config.enabled or len(window) < config.repetition_threshold:
        return False, None

    # 精确重复：最近 N 个指纹完全相同
    recent = window[-config.repetition_threshold :]
    keys = [_fp_key(fp) for fp in recent]
    if len(set(keys)) == 1:
        return True, f"Exact repetition detected for {recent[-1].get('name')}"

    # 相似重复：窗口内高相似度指纹占比过高
    if len(window) >= 2:
        sim_count = 0
        total = 0
        for i in range(len(window)):
            for j in range(i + 1, len(window)):
                total += 1
                if _similarity(window[i], window[j]) >= config.similarity_threshold:
                    sim_count += 1
        if total > 0 and sim_count / total >= 0.5:
            return True, "High similarity fingerprint cluster detected"

    return False, None
