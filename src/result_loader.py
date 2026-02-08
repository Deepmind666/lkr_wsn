#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified Result Loader for AERIS-WSN-Protocol

解决两种 JSON schema 的不一致问题：
1. unified_metrics schema: results 为 Array
2. dynamic_* schema: results 为嵌套 Dict

统一返回 flat list 格式，字段名标准化。
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


# 字段名映射：将各种命名统一到标准名称
FIELD_MAPPING = {
    # PDR 相关 - 注意区分链路级和端到端
    "pdr_end2end": "pdr_end2end",
    "packet_delivery_ratio_end2end": "pdr_end2end",
    "pdr": "pdr_hop",  # 链路级PDR
    "packet_delivery_ratio": "pdr_hop",  # 链路级PDR，不要误映射到端到端
    # 能耗相关
    "energy_total_j": "energy_total_j",
    "total_energy_consumed": "energy_total_j",
    # 存活节点
    "alive_nodes": "alive_nodes",
    "final_alive_nodes": "alive_nodes",
    # 延迟
    "avg_delay": "avg_delay",
    "average_delay": "avg_delay",
}

# 协议名映射：统一到新命名
PROTOCOL_MAPPING = {
    "AERIS_energy": "AERIS-E",
    "AERIS_robust": "AERIS-R",
    "AERIS-E": "AERIS-E",
    "AERIS-R": "AERIS-R",
    "LEACH": "LEACH",
    "HEED": "HEED",
    "PEGASIS": "PEGASIS",
    "TEEN": "TEEN",
}


def normalize_field_name(name: str) -> str:
    """将字段名标准化"""
    return FIELD_MAPPING.get(name, name)


def normalize_protocol_name(name: str) -> str:
    """将协议名标准化"""
    return PROTOCOL_MAPPING.get(name, name)


def extract_metrics(raw_metrics: Dict[str, Any]) -> Dict[str, Any]:
    """从原始 metrics 字典中提取并标准化字段"""
    normalized = {}
    for key, value in raw_metrics.items():
        norm_key = normalize_field_name(key)
        # 避免覆盖已存在的标准字段
        if norm_key not in normalized:
            normalized[norm_key] = value
    return normalized


def _flatten_dynamic_results(results: Dict[str, Any]) -> List[Dict[str, Any]]:
    """展平 dynamic schema 的嵌套 dict 结构"""
    flat = []
    for rep_key, phases in results.items():
        if not isinstance(phases, dict):
            continue
        for phase, protocols in phases.items():
            if not isinstance(protocols, dict):
                continue
            for proto, metrics in protocols.items():
                if not isinstance(metrics, dict):
                    continue
                record = {
                    "replicate": rep_key,
                    "phase": phase,
                    "protocol": normalize_protocol_name(proto),
                }
                record.update(extract_metrics(metrics))
                flat.append(record)
    return flat


def _normalize_unified_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """标准化 unified schema 的 list 结构"""
    normalized = []
    for item in results:
        record = {}
        # 复制非 metrics 字段
        for key, value in item.items():
            if key == "metrics" and isinstance(value, dict):
                record.update(extract_metrics(value))
            elif key == "protocol":
                record["protocol"] = normalize_protocol_name(value)
            else:
                record[key] = value
        normalized.append(record)
    return normalized


def detect_schema_type(data: Dict[str, Any]) -> str:
    """
    检测 JSON 数据的 schema 类型

    Returns:
        "unified" | "dynamic" | "unknown"
    """
    # 优先使用显式声明的 schema_type
    schema_type = data.get("schema_type", "")
    if schema_type == "unified_metrics":
        return "unified"
    if schema_type.startswith("dynamic_"):
        return "dynamic"

    # 根据 results 结构推断
    results = data.get("results")
    if isinstance(results, list):
        return "unified"
    if isinstance(results, dict):
        # 检查是否为 rep_* 嵌套结构
        keys = list(results.keys())
        if keys and all(k.startswith("rep_") for k in keys):
            return "dynamic"

    return "unknown"


def load_experiment_results(
    path: Union[str, Path],
    normalize_protocols: bool = True,
    normalize_fields: bool = True,
) -> List[Dict[str, Any]]:
    """
    统一加载实验结果，返回 flat list 格式

    Args:
        path: JSON 文件路径
        normalize_protocols: 是否标准化协议名 (AERIS_energy -> AERIS-E)
        normalize_fields: 是否标准化字段名 (packet_delivery_ratio_end2end -> pdr_end2end)

    Returns:
        List[Dict]: 每条记录包含 protocol, scenario/phase, 以及标准化的 metrics

    Raises:
        FileNotFoundError: 文件不存在
        ValueError: 无法识别的 schema 类型
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    schema = detect_schema_type(data)
    results = data.get("results")

    if schema == "unified":
        if not isinstance(results, list):
            raise ValueError(f"Expected list for unified schema, got {type(results)}")
        flat = _normalize_unified_results(results) if normalize_fields else results
    elif schema == "dynamic":
        if not isinstance(results, dict):
            raise ValueError(f"Expected dict for dynamic schema, got {type(results)}")
        flat = _flatten_dynamic_results(results)
    else:
        raise ValueError(f"Unknown schema type in {path}. Set schema_type explicitly.")

    return flat


def load_from_candidates(
    candidates: List[Union[str, Path]],
    **kwargs
) -> List[Dict[str, Any]]:
    """
    从候选文件列表中加载第一个存在的文件

    Args:
        candidates: 候选文件路径列表（按优先级排序）
        **kwargs: 传递给 load_experiment_results 的参数

    Returns:
        List[Dict]: 标准化的实验结果

    Raises:
        FileNotFoundError: 所有候选文件都不存在
    """
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return load_experiment_results(path, **kwargs)

    raise FileNotFoundError(f"No available files among {candidates}")


def get_metadata(path: Union[str, Path]) -> Dict[str, Any]:
    """
    获取实验文件的元数据

    Returns:
        Dict 包含: schema_type, n_results, format_version, metadata 等
    """
    path = Path(path)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    schema = detect_schema_type(data)
    results = data.get("results")

    # 计算实际记录数
    if schema == "unified" and isinstance(results, list):
        actual_count = len(results)
    elif schema == "dynamic" and isinstance(results, dict):
        actual_count = sum(
            len(protocols)
            for phases in results.values()
            if isinstance(phases, dict)
            for protocols in phases.values()
            if isinstance(protocols, dict)
        )
    else:
        actual_count = 0

    return {
        "schema_type": schema,
        "declared_n_results": data.get("n_results"),
        "actual_n_results": actual_count,
        "format_version": data.get("format_version"),
        "metadata": data.get("metadata", {}),
        "n_results_consistent": data.get("n_results") == actual_count,
    }


def validate_schema_consistency(path: Union[str, Path]) -> Dict[str, Any]:
    """
    验证文件的 schema 一致性

    Returns:
        Dict 包含验证结果和发现的问题
    """
    meta = get_metadata(path)
    issues = []

    if meta["schema_type"] == "unknown":
        issues.append("Cannot detect schema type")

    if not meta["n_results_consistent"]:
        issues.append(
            f"n_results mismatch: declared={meta['declared_n_results']}, "
            f"actual={meta['actual_n_results']}"
        )

    return {
        "path": str(path),
        "valid": len(issues) == 0,
        "issues": issues,
        "metadata": meta,
    }


# 便捷函数：按协议分组
def group_by_protocol(records: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """将记录按协议分组"""
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for record in records:
        proto = record.get("protocol", "unknown")
        grouped.setdefault(proto, []).append(record)
    return grouped


# 便捷函数：提取特定指标
def extract_metric(
    records: List[Dict[str, Any]],
    metric: str,
    protocol: Optional[str] = None,
) -> List[float]:
    """
    提取特定指标的值列表

    Args:
        records: 记录列表
        metric: 指标名（会自动标准化）
        protocol: 可选，只提取特定协议的数据

    Returns:
        List[float]: 指标值列表
    """
    norm_metric = normalize_field_name(metric)
    values = []
    for record in records:
        if protocol and record.get("protocol") != normalize_protocol_name(protocol):
            continue
        val = record.get(norm_metric)
        if val is not None:
            values.append(float(val))
    return values


if __name__ == "__main__":
    # 简单测试
    import sys
    if len(sys.argv) > 1:
        path = sys.argv[1]
        print(f"Loading: {path}")
        results = load_experiment_results(path)
        print(f"Loaded {len(results)} records")
        meta = get_metadata(path)
        print(f"Metadata: {meta}")
        validation = validate_schema_consistency(path)
        print(f"Validation: {validation}")
