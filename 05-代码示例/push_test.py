# SPDX-License-Identifier: MIT
"""
移动推送通知测试（FCM / APNs / 个推 / 极光）
被引用方：10-移动测试 agent
"""
import json
import logging
import os
import time
from typing import Dict, Optional

import requests

logger = logging.getLogger(__name__)


# ===== Firebase Cloud Messaging（Android + iOS via FCM）=====

def send_fcm_v1(project_id: str, access_token: str,
                 device_token: str, title: str, body: str,
                 data: Optional[Dict] = None) -> Dict:
    """FCM HTTP v1 API 发送"""
    url = f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
    payload = {
        "message": {
            "token": device_token,
            "notification": {"title": title, "body": body},
            "data": data or {},
        }
    }
    r = requests.post(url, json=payload, headers={
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }, timeout=10)
    return {"status_code": r.status_code, "body": r.json() if r.ok else r.text}


# ===== APNs（iOS 原生）=====

def send_apns(device_token: str, bundle_id: str,
              title: str, body: str,
              p8_key_path: str, key_id: str, team_id: str,
              env: str = "production") -> Dict:
    """
    Apple Push Notification service（HTTP/2，需 JWT 签名）
    依赖：pip install pyjwt
    """
    import jwt as pyjwt

    with open(p8_key_path) as f:
        private_key = f.read()
    token = pyjwt.encode({
        "iss": team_id, "iat": int(time.time()),
    }, private_key, algorithm="ES256", headers={"alg": "ES256", "kid": key_id})

    host = "api.push.apple.com" if env == "production" else "api.sandbox.push.apple.com"
    payload = {"aps": {"alert": {"title": title, "body": body}}}

    # 实际生产用 hyper / httpx HTTP/2；此处简化
    r = requests.post(
        f"https://{host}/3/device/{device_token}",
        json=payload,
        headers={
            "authorization": f"bearer {token}",
            "apns-topic": bundle_id,
        },
        timeout=10,
    )
    return {"status_code": r.status_code, "body": r.text[:200]}


# ===== DeepLink / Universal Link 验证 =====

def test_deeplink(scheme_url: str, expected_screen: str,
                   adb_serial: Optional[str] = None) -> Dict:
    """Android: adb shell am start 触发 deeplink，验证目标页"""
    import subprocess
    cmd = ["adb"]
    if adb_serial:
        cmd += ["-s", adb_serial]
    cmd += ["shell", "am", "start", "-W", "-a", "android.intent.action.VIEW", "-d", scheme_url]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    output = proc.stdout
    return {
        "scheme_url": scheme_url,
        "exit_code": proc.returncode,
        "output": output[:500],
        "matched_screen": expected_screen in output,
    }


# ===== 安装/升级测试 =====

def install_apk(apk_path: str, adb_serial: Optional[str] = None,
                replace: bool = False) -> Dict:
    """安装 APK；replace=True 等价于覆盖升级"""
    import subprocess
    cmd = ["adb"]
    if adb_serial:
        cmd += ["-s", adb_serial]
    cmd += ["install"]
    if replace:
        cmd += ["-r"]
    cmd += [apk_path]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    return {"success": "Success" in proc.stdout, "output": proc.stdout}


def uninstall_app(package: str, adb_serial: Optional[str] = None) -> Dict:
    import subprocess
    cmd = ["adb"]
    if adb_serial:
        cmd += ["-s", adb_serial]
    cmd += ["uninstall", package]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return {"success": "Success" in proc.stdout, "output": proc.stdout}


# ===== 后台杀进程恢复 =====

def kill_app_and_relaunch(package: str, activity: str,
                           adb_serial: Optional[str] = None) -> Dict:
    """模拟用户杀后台 → 重启，验证状态恢复"""
    import subprocess
    base = ["adb"] + (["-s", adb_serial] if adb_serial else [])
    subprocess.run(base + ["shell", "am", "force-stop", package], check=True, timeout=10)
    time.sleep(2)
    proc = subprocess.run(
        base + ["shell", "am", "start", "-n", f"{package}/{activity}"],
        capture_output=True, text=True, timeout=15,
    )
    return {"package": package, "restart_output": proc.stdout[:200]}


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="移动推送 & 专项测试")
    sub = parser.add_subparsers(dest="cmd")
    dl = sub.add_parser("deeplink"); dl.add_argument("url"); dl.add_argument("--expected", default="")
    inst = sub.add_parser("install"); inst.add_argument("apk"); inst.add_argument("--replace", action="store_true")
    rk = sub.add_parser("relaunch"); rk.add_argument("package"); rk.add_argument("activity")
    args = parser.parse_args()
    if args.cmd == "deeplink":
        print(json.dumps(test_deeplink(args.url, args.expected), indent=2, ensure_ascii=False))
    elif args.cmd == "install":
        print(json.dumps(install_apk(args.apk, replace=args.replace), indent=2))
    elif args.cmd == "relaunch":
        print(json.dumps(kill_app_and_relaunch(args.package, args.activity), indent=2))
