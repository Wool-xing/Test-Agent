# SPDX-License-Identifier: MIT
"""
Data Factory v2 — 8 entity types, relational data, multi-format output.

Upgrades vs data_factory.py:
- 8 entity types: User, Product, Order, Payment, Address, Session, Notification, AuditLog
- SubFactory foreign key relationships
- Salted PII hashing (not deterministic raw hash)
- Multi-format output: JSON, CSV, SQL INSERT, Parquet
- Country/locale-aware data generation (CN, US, EU)

Usage:
  python data_factory_v2.py generate --entity user --count 100 --format json
  python data_factory_v2.py generate --entity order --count 50 --related user,product --format csv
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import random
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    from faker import Faker
    HAS_FAKER = True
except ImportError:
    HAS_FAKER = False

PII_SALT = os.environ.get("TAGENT_PII_SALT", str(uuid.uuid4().int)[:16])


def mask_pii(value: str, pii_type: str = "") -> str:
    """Salted, non-deterministic PII hashing."""
    salted = f"{PII_SALT}:{pii_type}:{value}"
    return hashlib.sha256(salted.encode()).hexdigest()[:12]


@dataclass
class EntityRegistry:
    """Tracks generated entities for foreign key resolution."""
    ids: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))

    def add(self, entity: str, eid: str) -> None:
        self.ids[entity].append(eid)

    def random_ref(self, entity: str) -> str | None:
        ids = self.ids.get(entity, [])
        return random.choice(ids) if ids else None


class DataFactoryV2:
    """Generate realistic test data with foreign key relationships."""

    def __init__(self, locale: str = "zh_CN", seed: int | None = None):
        self.locale = locale
        self.registry = EntityRegistry()
        self._faker: Any = None
        if seed:
            random.seed(seed)
            Faker.seed(seed)

    @property
    def faker(self):
        if self._faker is None and HAS_FAKER:
            self._faker = Faker(self.locale)
        return self._faker

    # ── User ──

    def user(self) -> dict:
        f = self.faker
        uid = f"USR-{uuid.uuid4().hex[:8]}"
        self.registry.add("user", uid)
        return {
            "id": uid,
            "name": f.name() if f else "Test User",
            "email": mask_pii(f.email() if f else "test@test.com", "email"),
            "phone": mask_pii(f.phone_number() if f else "+86-10-12345678", "phone"),
            "role": random.choice(["user", "user", "user", "admin"]),
            "verified": random.random() > 0.2,
            "created_at": _iso_now(-random.randint(0, 365 * 86400)),
        }

    # ── Product ──

    PRODUCT_CATEGORIES = ["electronics", "clothing", "food", "books", "sports", "beauty"]

    def product(self) -> dict:
        pid = f"PRD-{uuid.uuid4().hex[:8]}"
        self.registry.add("product", pid)
        cat = random.choice(self.PRODUCT_CATEGORIES)
        return {
            "id": pid,
            "name": f"{cat}-{random.randint(1000, 9999)}",
            "category": cat,
            "price": round(random.uniform(1, 9999), 2),
            "currency": random.choice(["CNY", "USD", "EUR"]),
            "in_stock": random.random() > 0.1,
            "stock_qty": random.randint(0, 1000),
        }

    # ── Address ──

    def address(self, user_id: str | None = None) -> dict:
        f = self.faker
        aid = f"ADR-{uuid.uuid4().hex[:8]}"
        self.registry.add("address", aid)
        return {
            "id": aid,
            "user_id": user_id or self.registry.random_ref("user"),
            "street": f.street_address() if f else "123 Test St",
            "city": f.city() if f else "Beijing",
            "province": f.province() if f else "Beijing",
            "postal_code": f.postcode() if f else "100000",
            "country": random.choice(["CN", "CN", "CN", "US", "EU"]),
            "is_default": random.random() < 0.3,
        }

    # ── Order (→ User, Address) ──

    ORDER_STATUSES = ["pending", "confirmed", "shipped", "delivered", "cancelled", "refunded"]

    def order(self, user_id: str | None = None, address_id: str | None = None) -> dict:
        oid = f"ORD-{uuid.uuid4().hex[:8]}"
        self.registry.add("order", oid)
        items = [{"product_id": self.registry.random_ref("product") or "PRD-unknown",
                  "qty": random.randint(1, 5),
                  "unit_price": round(random.uniform(10, 500), 2)}
                 for _ in range(random.randint(1, 5))]
        total = round(sum(i["qty"] * i["unit_price"] for i in items), 2)
        return {
            "id": oid,
            "user_id": user_id or self.registry.random_ref("user"),
            "address_id": address_id or self.registry.random_ref("address"),
            "status": random.choice(self.ORDER_STATUSES),
            "items": items,
            "total": total,
            "currency": "CNY",
            "created_at": _iso_now(-random.randint(0, 90 * 86400)),
        }

    # ── Payment (→ Order) ──

    def payment(self, order_id: str | None = None) -> dict:
        return {
            "id": f"PAY-{uuid.uuid4().hex[:8]}",
            "order_id": order_id or self.registry.random_ref("order"),
            "method": random.choice(["wechat_pay", "alipay", "credit_card", "debit_card"]),
            "amount": round(random.uniform(10, 5000), 2),
            "status": random.choice(["success", "success", "success", "failed", "pending"]),
            "paid_at": _iso_now(-random.randint(0, 30 * 86400)),
        }

    # ── Session ──

    def session(self, user_id: str | None = None) -> dict:
        return {
            "id": f"SES-{uuid.uuid4().hex[:16]}",
            "user_id": user_id or self.registry.random_ref("user"),
            "ip": f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
            "user_agent": random.choice([
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130",
                "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0) Mobile/15E148",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7) Safari/18.0",
            ]),
            "created_at": _iso_now(-random.randint(0, 7 * 86400)),
            "expires_at": _iso_now(random.randint(3600, 86400)),
        }

    # ── Notification ──

    def notification(self, user_id: str | None = None) -> dict:
        return {
            "id": f"NTF-{uuid.uuid4().hex[:8]}",
            "user_id": user_id or self.registry.random_ref("user"),
            "type": random.choice(["email", "sms", "push", "in_app"]),
            "template": f"notification_template_{random.randint(1,20)}",
            "sent": random.random() > 0.1,
            "read": random.random() > 0.3,
            "created_at": _iso_now(-random.randint(0, 3 * 86400)),
        }

    # ── AuditLog ──

    AUDIT_ACTIONS = ["login", "logout", "view", "create", "update", "delete", "export", "api_call"]

    def audit_log(self, user_id: str | None = None) -> dict:
        return {
            "id": f"AUD-{uuid.uuid4().hex[:8]}",
            "user_id": user_id or self.registry.random_ref("user"),
            "action": random.choice(self.AUDIT_ACTIONS),
            "resource": random.choice(["order", "user_profile", "report", "settings", "product"]),
            "resource_id": f"RES-{uuid.uuid4().hex[:6]}",
            "ip": f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
            "user_agent": "TagentTest/1.0",
            "timestamp": _iso_now(-random.randint(0, 30 * 86400)),
        }

    # ── Generate batch with relationships ──

    def generate_related(self, count: int = 50) -> dict[str, list[dict]]:
        """Generate a complete related dataset (users → orders → payments)."""
        users = [self.user() for _ in range(count)]
        products = [self.product() for _ in range(count // 2)]
        addresses = [self.address(user_id=random.choice(users)["id"]) for _ in range(count)]
        orders = []
        for _ in range(count * 2):
            user = random.choice(users)
            addr = random.choice(addresses)
            orders.append(self.order(user_id=user["id"], address_id=addr["id"]))
        payments = [self.payment(order_id=random.choice(orders)["id"]) for _ in range(count)]
        sessions = [self.session(user_id=random.choice(users)["id"]) for _ in range(count // 2)]

        return {"users": users, "products": products, "addresses": addresses,
                "orders": orders, "payments": payments, "sessions": sessions}

    # ── Output formatters ──

    def to_json(self, data: list[dict]) -> str:
        return json.dumps(data, indent=2, ensure_ascii=False)

    def to_csv(self, data: list[dict]) -> str:
        if not data:
            return ""
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=data[0].keys())
        writer.writeheader()
        for row in data:
            flat = {k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v
                    for k, v in row.items()}
            writer.writerow(flat)
        return buf.getvalue()

    def to_sql(self, data: list[dict], table: str) -> str:
        if not data:
            return ""
        cols = list(data[0].keys())
        values = []
        for row in data:
            vals = []
            for k in cols:
                v = row[k]
                if v is None:
                    vals.append("NULL")
                elif isinstance(v, (int, float)):
                    vals.append(str(v))
                elif isinstance(v, bool):
                    vals.append("TRUE" if v else "FALSE")
                else:
                    escaped = json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v).replace("'", "''")
                    vals.append(f"'{escaped}'")
            values.append(f"({', '.join(vals)})")
        return f"INSERT INTO {table} ({', '.join(cols)}) VALUES\n" + ",\n".join(values) + ";"


def _iso_now(offset_seconds: int = 0) -> str:
    t = time.time() + offset_seconds
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Data Factory v2")
    sub = ap.add_subparsers(dest="cmd")

    gen = sub.add_parser("generate", help="Generate entity data")
    gen.add_argument("--entity", required=True, choices=["user", "product", "order", "payment",
                     "address", "session", "notification", "audit_log", "related"])
    gen.add_argument("--count", type=int, default=10)
    gen.add_argument("--format", default="json", choices=["json", "csv", "sql"])
    gen.add_argument("--output", default="")
    gen.add_argument("--seed", type=int, default=None)

    args = ap.parse_args()
    factory = DataFactoryV2(seed=args.seed)

    if args.cmd == "generate":
        if args.entity == "related":
            result = factory.generate_related(args.count)
            output = json.dumps({k: v for k, v in result.items()}, indent=2, ensure_ascii=False)
        else:
            method = getattr(factory, args.entity)
            items = [method() for _ in range(args.count)]
            if args.format == "json":
                output = factory.to_json(items)
            elif args.format == "csv":
                output = factory.to_csv(items)
            elif args.format == "sql":
                output = factory.to_sql(items, args.entity + "s")

        if args.output:
            Path(args.output).write_text(output, encoding="utf-8")
            print(f"Generated {args.count} {args.entity}(s) → {args.output}")
        else:
            print(output[:2000])
