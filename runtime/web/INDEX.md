# runtime/web 索引(V1.2.0 MVP)

> Web UI for `runtime/api`. 4 页:Upload / Run Status / Report / Catalog。
> 被测项级别 §21 **L2**(用户可见,必含功能+边界+异常+兼容+可访问性测试)。

## 技术栈

| 项 | 选 |
|----|----|
| 构建 | Vite 5 + TypeScript 5 |
| UI 框架 | React 18 |
| 组件库 | shadcn/ui (Radix + Tailwind) |
| 数据请求 | TanStack Query v5 |
| 路由 | React Router v7 |
| 上传 | tus-js-client(断点续传,大文件友好) |
| 流式状态 | EventSource(SSE)对 `/status/{run_id}` |
| 测试 | Vitest 单元 + Playwright E2E + axe-core 可访问性 |

## 4 页

| 路由 | 用途 |
|------|------|
| `/` | Upload(多格式:PDF/Word/MD/exe/APK/IPA/Docker/URL/口头) |
| `/runs/:run_id` | Run Status(SSE 流式 DAG 实时进度) |
| `/runs/:run_id/report` | Report(执行结果+证据+缺陷链接) |
| `/catalog` | 16 专家 + 32 skill 目录 |

## 启动

```bash
cd runtime/web
npm install
npm run dev          # Vite dev server :5173
npm run build        # 产出 dist/
npm run test         # Vitest
npm run test:e2e     # Playwright
npm run test:a11y    # axe-core 可访问性扫
```

## API 端点对接

| 前端 | 后端(`runtime/api/main.py`) |
|------|-----------------------------|
| Upload 文本 | `POST /run/text` |
| Upload 文件 | `POST /run/file` |
| Upload URL | `POST /run/url` |
| Status | `GET /status/{run_id}` |
| Report | `GET /report/{run_id}` |
| Catalog | `GET /catalog` |
| Health | `GET /health` |

## §21 必测项(L2 级)

- 功能正常路径:上传→看 DAG→看报告
- 边界:超大文件/空文本/超长 run_id
- 异常:API 502 / 超时 / 网络断开
- 兼容:Chrome / Firefox / Safari / Edge
- 可访问性:axe-core 0 critical + WCAG 2.1 AA

## 不在本期(M2)

- 国际化 i18n(M3)
- 暗色模式(M3)
- 多用户认证(M3)
- 编辑/重跑/对比 历史 runs(M3)
