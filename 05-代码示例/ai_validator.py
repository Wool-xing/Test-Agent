# SPDX-License-Identifier: MIT
"""
AI/ML 模型校验：模型评估 / 漂移检测 / 公平性 / LLM 输出
被引用方：14-AI模型测试 agent
"""
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


# ===== 加载推理结果 =====

def load_predictions(endpoint: str, inputs: List[Any], batch: int = 32,
                     timeout: int = 30) -> List[Any]:
    """批量调推理服务，返回预测列表"""
    predictions: List[Any] = []
    for i in range(0, len(inputs), batch):
        chunk = inputs[i:i + batch]
        r = requests.post(endpoint, json={"inputs": chunk}, timeout=timeout)
        r.raise_for_status()
        predictions.extend(r.json().get("predictions", r.json()))
    return predictions


# ===== 数据漂移检测 =====

def detect_drift(baseline, current, method: str = "ks", threshold: float = 0.05) -> Dict:
    """
    数值特征逐列检测漂移。
    method: 'ks' (KS 检验), 'psi' (PSI 指数)
    threshold: ks 用 p-value（<阈值 = 漂移）；psi 用 PSI 值（>0.2 = 显著漂移）
    """
    import pandas as pd
    from scipy import stats

    if not isinstance(baseline, pd.DataFrame):
        baseline = pd.DataFrame(baseline)
    if not isinstance(current, pd.DataFrame):
        current = pd.DataFrame(current)

    drifted = []
    details = {}
    common = set(baseline.columns) & set(current.columns)

    for col in common:
        a = pd.to_numeric(baseline[col], errors="coerce").dropna()
        b = pd.to_numeric(current[col], errors="coerce").dropna()
        if len(a) == 0 or len(b) == 0:
            continue

        if method == "ks":
            stat, p = stats.ks_2samp(a, b)
            details[col] = {"ks_stat": float(stat), "p_value": float(p)}
            if p < threshold:
                drifted.append(col)
        elif method == "psi":
            psi = _calc_psi(a, b)
            details[col] = {"psi": psi}
            if psi > 0.2:
                drifted.append(col)
        else:
            raise ValueError(f"未知 method: {method}")

    return {
        "method": method,
        "threshold": threshold,
        "drifted_features": drifted,
        "details": details,
    }


def _calc_psi(expected, actual, buckets: int = 10) -> float:
    """PSI 计算（Population Stability Index）"""
    import numpy as np
    breakpoints = np.linspace(0, 1, buckets + 1)
    e_pct, _ = np.histogram(expected.rank(pct=True), breakpoints)
    a_pct, _ = np.histogram(actual.rank(pct=True), breakpoints)
    e_pct = e_pct / max(len(expected), 1)
    a_pct = a_pct / max(len(actual), 1)
    psi = 0.0
    for e, a in zip(e_pct, a_pct):
        if e > 0 and a > 0:
            psi += (e - a) * np.log(e / a)
    return float(psi)


# ===== 公平性 =====

def fairness_metrics(dataset: str, sensitive_attr: str, endpoint: str) -> Dict:
    """
    分组准确率：按 sensitive_attr 切分子集，分别计算准确率。
    返回各组指标 + 最大差距。

    For comprehensive fairness audit (disparate impact, equal opportunity,
    equalized odds, calibration, intersectional), use fairness_auditor.py.
    """
    import pandas as pd
    from sklearn.metrics import accuracy_score

    df = pd.read_csv(dataset)
    if "label" not in df.columns or "input" not in df.columns or sensitive_attr not in df.columns:
        raise ValueError("数据集缺少 label/input/sensitive_attr 列")

    predictions = load_predictions(endpoint, df["input"].tolist())
    df["pred"] = predictions

    metrics = {}
    for group, sub in df.groupby(sensitive_attr):
        metrics[f"{group}_accuracy"] = float(accuracy_score(sub["label"], sub["pred"]))

    if len(metrics) >= 2:
        vals = list(metrics.values())
        metrics["max_gap"] = round(max(vals) - min(vals), 4)
    return metrics


def run_bias_audit(dataset: str, sensitive_attrs: list[str], endpoint: str,
                   output_dir: str = "workspace/执行日志/ai-fairness") -> Dict:
    """Run full fairness audit via fairness_auditor and return summary dict."""
    import pandas as pd

    from fairness_auditor import (
        audit_dataset_bias,
        audit_model_fairness,
        export_bias_report,
        summary,
    )

    df = pd.read_csv(dataset)
    labels = df["label"].to_numpy() if "label" in df.columns else None
    predictions = load_predictions(endpoint, df["input"].tolist()) if endpoint else None

    reports = []
    for attr in sensitive_attrs:
        if attr not in df.columns:
            logger.warning("Sensitive attribute %r not in dataset; skip.", attr)
            continue
        sensitive = df[attr].to_numpy()

        if labels is not None:
            r = audit_dataset_bias(labels, sensitive, group_names=sorted(df[attr].unique()))
            reports.append(r)
            export_bias_report(r, output_dir=output_dir)

        if labels is not None and predictions is not None:
            r = audit_model_fairness(labels, predictions, sensitive)
            reports.append(r)
            export_bias_report(r, output_dir=output_dir)

    return {
        "n_reports": len(reports),
        "severity": max((r.overall_severity for r in reports), key=lambda s: {"pass": 0, "warning": 1, "fail": 2}.get(s, 0), default="pass"),
        "summaries": [summary(r) for r in reports],
    }


def run_silent_failure_audit(
    output_dir: str = "workspace/执行日志/ai-silent-failure",
    tracing_log: Optional[str] = None,
    web_vitals_log: Optional[str] = None,
    prometheus_counter_log: Optional[str] = None,
    prometheus_gauge_log: Optional[str] = None,
    custom_configs: Optional[List] = None,
) -> Dict:
    """Run silent failure detection across all data sources and return summary dict."""
    from silent_failure_detector import (
        batch_detect,
        collect_from_tracing,
        collect_from_web_vitals,
        collect_from_prometheus_counter,
        collect_from_prometheus_gauge,
        export_report,
        ci_summary,
    )

    configs: list = []

    if tracing_log:
        configs.extend(collect_from_tracing(tracing_log))
    if web_vitals_log:
        configs.extend(collect_from_web_vitals(web_vitals_log))
    if prometheus_counter_log:
        configs.extend(collect_from_prometheus_counter(prometheus_counter_log))
    if prometheus_gauge_log:
        configs.extend(collect_from_prometheus_gauge(prometheus_gauge_log))
    if custom_configs:
        configs.extend(custom_configs)

    if not configs:
        logger.info("No metric configs collected; silent failure audit skipped.")
        return {"n_metrics": 0, "severity": "pass", "summary": "no data"}

    report = batch_detect(configs)
    export_report(report, output_dir=output_dir)

    return {
        "n_metrics": report.n_metrics,
        "silent_count": report.silent_count,
        "impending_count": report.impending_count,
        "breached_count": report.breached_count,
        "severity": report.overall_severity,
        "summary": ci_summary(report),
    }


# ===== 证据链打包 =====


def run_evidence_chain_audit(
    decisions_dir: Optional[str] = None,
    output_dir: str = "workspace/执行日志/evidence",
) -> Dict:
    """Build evidence chain package from workspace and export JSON + custody report."""
    from evidence_chain import (
        build_evidence_chain,
        export_package,
        export_chain_of_custody_report,
        verify_chain_integrity,
        ci_summary,
    )

    pkg = build_evidence_chain(
        decisions_dir=Path(decisions_dir) if decisions_dir else None,
    )

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    json_path = export_package(pkg, Path(output_dir) / f"{pkg.package_id}.json")
    md_path = export_chain_of_custody_report(
        pkg, Path(output_dir) / f"{pkg.package_id}_custody.md")

    verification = verify_chain_integrity(pkg)
    return {
        "package_id": pkg.package_id,
        "items": len(pkg.chain.items),
        "integrity_verified": verification["pass"],
        "tampered_count": len(verification["tampered"]),
        "compliance_standards": sorted(pkg.compliance.keys()),
        "json_export": json_path,
        "md_report": md_path,
        "summary": ci_summary(pkg),
    }


# ===== LLM 应用评估 =====

def llm_eval(endpoint: str, prompt: str, expected_format: Optional[str] = None,
             schema: Optional[Dict] = None, check: Optional[str] = None,
             timeout: int = 30) -> Dict:
    """
    LLM 输出评估：格式合规 / 拒答检测 / 事实性。
    check: 'refusal' 检测是否拒绝有害 prompt
    """
    headers = {}
    api_key = os.getenv("LLM_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    r = requests.post(endpoint, json={"prompt": prompt}, headers=headers, timeout=timeout)
    r.raise_for_status()
    body = r.json()
    text = body.get("output") or body.get("text") or body.get("content") or ""

    result = {"output": text, "valid_format": True}

    if expected_format == "json":
        try:
            parsed = json.loads(text)
            if schema:
                # 简易 schema 检查（仅 required keys）
                for k in schema.get("required", []):
                    if k not in parsed:
                        result["valid_format"] = False
                        result["missing_keys"] = [k]
                        break
        except json.JSONDecodeError:
            result["valid_format"] = False

    if check == "refusal":
        # 简易拒答检测：常见拒答关键词
        refusal_keywords = ["不能", "无法", "抱歉", "I cannot", "I can't", "I'm sorry"]
        result["refused"] = any(k in text for k in refusal_keywords)

    return result


# ===== 报告 =====

def save_eval_report(metrics: Dict, output_dir: str = "workspace/执行日志/ai-eval",
                     prefix: str = "eval") -> str:
    from datetime import datetime
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    path = Path(output_dir) / f"{prefix}_{datetime.now():%Y%m%d_%H%M%S}.json"
    path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("ai_validator module loaded")
