"""
小程序自动化运行器
依赖：微信开发者工具 CLI（命令行启动自动化端口）+ miniprogram-automator npm 模块（外部）
当前实现：通过 subprocess 调微信 CLI + 走 ws 协议（用 websocket-client 简化）
被引用方：10-移动测试 agent / mobile-test skill（小程序场景）
"""
import json
import logging
import os
import subprocess
import time
from typing import Optional

logger = logging.getLogger(__name__)


class WxMiniProgram:
    """微信小程序自动化简化封装。
    建议生产环境用 miniprogram-automator（npm）+ Node 桥接。
    本实现仅提供常用方法骨架，复杂场景请扩展。
    """

    def __init__(self, port: int = 9420, project_path: Optional[str] = None):
        self.port = port
        self.project_path = project_path or os.getenv("WX_PROJECT_PATH", "")
        self.cli = os.getenv("WX_DEVTOOL_CLI", "")
        self._proc = None

    def open(self):
        """打开开发者工具 + 自动化端口"""
        if not self.cli:
            raise RuntimeError("WX_DEVTOOL_CLI 未配置")
        cmd = [self.cli, "auto", "--project", self.project_path, "--auto-port", str(self.port)]
        self._proc = subprocess.Popen(cmd)
        time.sleep(5)
        logger.info(f"微信开发者工具已启动，自动化端口 {self.port}")
        return self

    def close(self):
        if self._proc:
            self._proc.terminate()
            self._proc.wait(timeout=10)
            logger.info("微信开发者工具已关闭")

    # ----- ws 协议简化 -----

    def _send(self, method: str, params: Optional[dict] = None) -> dict:
        """通过 websocket 调用 mini-program-automator 协议（简化）"""
        try:
            import websocket
        except ImportError:
            raise RuntimeError("缺少 websocket-client，pip install websocket-client")
        ws = websocket.create_connection(f"ws://127.0.0.1:{self.port}", timeout=30)
        msg = {"id": int(time.time() * 1000), "method": method, "params": params or {}}
        ws.send(json.dumps(msg))
        resp = json.loads(ws.recv())
        ws.close()
        return resp

    def reLaunch(self, path: str):
        return self._send("Page.reLaunch", {"url": path})

    def navigateTo(self, path: str):
        return self._send("Page.navigateTo", {"url": path})

    def current_path(self) -> str:
        r = self._send("App.currentPage")
        return r.get("result", {}).get("path", "")

    def fill(self, selector: str, value: str):
        return self._send("Element.input", {"selector": selector, "value": value})

    def tap(self, selector: str):
        return self._send("Element.tap", {"selector": selector})

    def screenshot(self, output: str):
        r = self._send("App.screenshot")
        if "result" in r and "data" in r["result"]:
            import base64
            from pathlib import Path
            Path(output).parent.mkdir(parents=True, exist_ok=True)
            Path(output).write_bytes(base64.b64decode(r["result"]["data"]))
        return output


def connect(port: int = 9420, project_path: Optional[str] = None) -> WxMiniProgram:
    """快捷连接已启动的开发者工具自动化端口"""
    return WxMiniProgram(port=port, project_path=project_path)


def run_test(mp: WxMiniProgram, steps: list) -> bool:
    """简易执行器：按 step 列表顺序执行"""
    for step in steps:
        action = step["action"]
        if hasattr(mp, action):
            getattr(mp, action)(**step.get("args", {}))
        else:
            logger.error(f"未知 action: {action}")
            return False
    return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    mp = WxMiniProgram()
    print(f"WxMiniProgram ready (port={mp.port})")
