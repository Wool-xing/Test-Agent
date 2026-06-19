# backends 索引

> Agent**不绑笔记本**:7 后端任选,Serverless hibernate 几乎零成本。

## 7 后端

| 后端 | 文件 | 场景 |
| ------ | ------ | ------ |
|**local**| `local.py` | 本机直跑(subprocess) |
|**docker**| `docker.py` | 容器隔离 |
|**ssh**| `ssh.py` | 远程主机长连接(paramiko) |
|**singularity**| `singularity.py` | HPC 集群(SLURM 友好) |
|**modal**| `modal.py` | Serverless 持久化,闲置 hibernate |
|**daytona**| `daytona.py` | Serverless dev sandbox |
|**vercel_sandbox**| `vercel_sandbox.py` | 边缘运行 |

## 接口契约(`base.py`)

```python
class BaseExecutionEnv(abc.ABC):
    async def connect(self) -> None
    async def exec(self, cmd: str, *, timeout: float = 60) -> ExecResult
    async def read(self, path: str) -> bytes
    async def write(self, path: str, data: bytes) -> None
    async def sync_in(self, local: Path, remote: str) -> None
    async def sync_out(self, remote: str, local: Path) -> None
    async def close(self) -> None

```text

## 经济模型

- $5 VPS = local/docker 后端跑得起
- Serverless hibernate = modal/daytona 闲置零成本
- HPC = singularity 大算力突发
- 边缘 = vercel_sandbox 全球分布
