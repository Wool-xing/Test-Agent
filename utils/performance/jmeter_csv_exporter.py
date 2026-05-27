# SPDX-License-Identifier: MIT
"""
JMeter 参数化 CSV 文件生成
被引用方：05-数据准备 agent / data-preparation skill / CI yml/groovy
"""
import csv
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def export_to_jmeter_csv(
    users: List[Dict],
    output_path: str = "workspace/测试数据/jmeter_users.csv",
    fields: Optional[List[str]] = None,
) -> str:
    """
    从用户字典列表导出 JMeter 参数化 CSV。
    第一行为字段名（JMeter CSVDataSet variableNames）。
    """
    if fields is None:
        fields = ["username", "password", "user_id"]

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for u in users:
            writer.writerow({k: u.get(k, "") for k in fields})

    logger.info(f"JMeter CSV 已生成：{output_path}（{len(users)} 条记录）")
    return output_path


def generate_jmeter_dataset(
    count: int = 50,
    output_path: str = "workspace/测试数据/jmeter_users.csv",
    fields: Optional[List[str]] = None,
) -> str:
    """
    批量生成并导出 JMeter 压测专用用户数据。
    count 建议 = JMeter 并发线程数（确保每个虚拟用户独立账号）。
    """
    from utils.data.data_factory import UserFactory
    users = [UserFactory() for _ in range(count)]
    return export_to_jmeter_csv(users, output_path, fields)


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="生成 JMeter 参数化 CSV")
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--output", default="workspace/测试数据/jmeter_users.csv")
    args = parser.parse_args()
    generate_jmeter_dataset(args.count, args.output)
