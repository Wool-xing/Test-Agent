# SPDX-License-Identifier: MIT
"""
区块链 / 智能合约测试
被引用方：DApp / Web3 / DeFi 项目

依赖（按需）：
- web3.py（以太坊 + EVM 链）
- 外部工具：Hardhat / Foundry / Anvil（本地测试链）
"""
import json
import logging
import subprocess
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ===== Web3 基础检查 =====

def get_web3(rpc_url: str):
    """连接 RPC（Infura / Alchemy / 本地 anvil）"""
    try:
        from web3 import Web3
    except ImportError:
        raise RuntimeError("web3 未安装：pip install web3")
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        raise RuntimeError(f"RPC 连接失败: {rpc_url}")
    return w3


def chain_info(rpc_url: str) -> Dict:
    """链基础信息"""
    w3 = get_web3(rpc_url)
    return {
        "chain_id": w3.eth.chain_id,
        "block_number": w3.eth.block_number,
        "gas_price_gwei": w3.eth.gas_price / 10**9,
    }


# ===== 合约调用 =====

def call_contract_view(rpc_url: str, contract_address: str, abi: List[Dict],
                        method: str, *args) -> Any:
    """调用 view / pure 函数（不消耗 gas）"""
    w3 = get_web3(rpc_url)
    contract = w3.eth.contract(address=contract_address, abi=abi)
    func = getattr(contract.functions, method)
    return func(*args).call()


def estimate_gas(rpc_url: str, contract_address: str, abi: List[Dict],
                  method: str, sender: str, *args) -> int:
    w3 = get_web3(rpc_url)
    contract = w3.eth.contract(address=contract_address, abi=abi)
    func = getattr(contract.functions, method)
    return func(*args).estimate_gas({"from": sender})


# ===== 智能合约安全 =====

SLITHER_DETECTORS = [
    "reentrancy-eth", "reentrancy-no-eth", "uninitialized-state",
    "uninitialized-storage", "tx-origin", "delegatecall",
    "arbitrary-send", "controlled-array-length",
]


def run_slither(contract_path: str) -> Dict:
    """
    用 Slither 静态分析智能合约。需 pip install slither-analyzer + solc。
    """
    cmd = ["slither", contract_path, "--json", "-"]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    try:
        data = json.loads(proc.stdout) if proc.stdout else {"results": {}}
    except json.JSONDecodeError:
        return {"error": proc.stderr[-500:] if proc.stderr else "slither 输出解析失败"}

    detectors = data.get("results", {}).get("detectors", [])
    by_impact = {"High": 0, "Medium": 0, "Low": 0, "Informational": 0}
    for d in detectors:
        by_impact[d.get("impact", "Low")] = by_impact.get(d.get("impact", "Low"), 0) + 1

    return {
        "contract": contract_path,
        "total_findings": len(detectors),
        "by_impact": by_impact,
        "findings": [
            {"check": d.get("check"), "impact": d.get("impact"),
             "description": d.get("description", "")[:200]}
            for d in detectors[:20]
        ],
    }


# ===== 模糊测试 / Invariant Testing（Foundry 风格）=====

def run_foundry_invariant(project_dir: str, test_name: str = "") -> Dict:
    """
    Foundry forge test（含 invariant testing）。需安装 Foundry。
    """
    cmd = ["forge", "test", "--summary"]
    if test_name:
        cmd += ["--match-test", test_name]
    proc = subprocess.run(cmd, cwd=project_dir, capture_output=True, text=True, timeout=600)
    return {
        "exit_code": proc.returncode,
        "passed": "passed" in proc.stdout.lower(),
        "output_tail": proc.stdout[-1000:],
    }


# ===== Gas 消耗回归 =====

def gas_regression(current: int, baseline: int, threshold_pct: float = 5.0) -> Dict:
    """检测 gas 消耗回归（变更后比基线高 >threshold% → 告警）"""
    if baseline <= 0:
        return {"current": current, "baseline": baseline, "regression": False}
    pct = (current - baseline) / baseline * 100
    return {
        "current_gas": current,
        "baseline_gas": baseline,
        "change_pct": round(pct, 2),
        "regression": pct > threshold_pct,
    }


# ===== 区块链测试常见场景 =====

BLOCKCHAIN_TEST_SCENARIOS = """
□ 合约部署 + 初始化（owner / admin / 参数）
□ 函数访问控制（modifier onlyOwner）
□ 重入攻击（reentrancy）防护
□ 整数溢出（Solidity 0.8+ 自动 revert，旧版需 SafeMath）
□ 拒绝服务（block gas limit / unbounded loop）
□ 时间依赖（block.timestamp 操纵）
□ 随机性（链上随机不安全，需 Chainlink VRF）
□ 升级机制（proxy pattern 测试）
□ Gas 优化回归
□ 事件（event）正确触发
□ 多签 / Timelock / 治理流程
□ 与外部合约交互（链下 oracle）
"""


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="区块链 / 智能合约测试")
    sub = parser.add_subparsers(dest="cmd")
    info = sub.add_parser("info"); info.add_argument("--rpc", required=True)
    sl = sub.add_parser("slither"); sl.add_argument("contract")
    fd = sub.add_parser("foundry"); fd.add_argument("project_dir"); fd.add_argument("--test", default="")
    sub.add_parser("scenarios")
    args = parser.parse_args()
    if args.cmd == "info":
        print(json.dumps(chain_info(args.rpc), indent=2))
    elif args.cmd == "slither":
        print(json.dumps(run_slither(args.contract), indent=2, ensure_ascii=False))
    elif args.cmd == "foundry":
        print(json.dumps(run_foundry_invariant(args.project_dir, args.test), indent=2))
    elif args.cmd == "scenarios":
        print(BLOCKCHAIN_TEST_SCENARIOS)
