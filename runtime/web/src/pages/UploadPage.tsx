import { useState, FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { postRunFile, postRunText, postRunUrl, RunCreated } from "@/api";
import { Lightbulb, X } from "lucide-react";

type Mode = "text" | "file" | "url";

export default function UploadPage() {
  const [mode, setMode] = useState<Mode>("text");
  const [showGuide, setShowGuide] = useState(!localStorage.getItem("tagent_onboarded"));
  const [text, setText] = useState("");
  const [url, setUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [extra, setExtra] = useState("");
  const nav = useNavigate();

  const submit = useMutation({
    mutationFn: async (): Promise<RunCreated> => {
      if (mode === "text") return postRunText(text, extra ? { note: extra } : {});
      if (mode === "url") return postRunUrl(url);
      if (mode === "file" && file) return postRunFile(file, extra);
      throw new Error("invalid input");
    },
    onSuccess: (d) => nav(`/runs/${d.run_id}`),
  });

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    submit.mutate();
  };

  return (
    <section aria-labelledby="upload-heading" className="max-w-2xl">
      <h2 id="upload-heading" className="text-2xl font-bold mb-4">
        新建测试任务
      </h2>
      <p className="text-sm text-slate-600 mb-4">
        支持文本指令、文件上传(PDF/Word/MD/exe/APK/IPA/Docker)、或被测系统 URL。
      </p>

      {showGuide && (
        <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg text-sm space-y-2">
          <div className="flex items-center justify-between">
            <span className="font-medium flex items-center gap-1.5"><Lightbulb className="w-4 h-4" /> Quick Start</span>
            <button onClick={() => { setShowGuide(false); localStorage.setItem("tagent_onboarded", "1"); }} className="text-slate-400 hover:text-slate-600"><X className="w-4 h-4" /></button>
          </div>
          <ol className="list-decimal list-inside space-y-1 text-slate-600">
            <li>Enter a test target (e.g. "Login page at https://example.com")</li>
            <li>Click <strong>Start Test</strong> — AI plans & runs the test</li>
            <li>Watch progress in real-time → view report</li>
            <li>Go to <strong>Settings</strong> to add your LLM API key for smarter results</li>
            <li>Check <strong>System Check</strong> to verify everything works</li>
          </ol>
        </div>
      )}

      <fieldset className="mb-4" role="radiogroup" aria-labelledby="mode-legend">
        <legend id="mode-legend" className="text-sm font-medium mb-2">
          输入方式
        </legend>
        <div className="flex gap-3" role="radiogroup">
          {(["text", "file", "url"] as Mode[]).map((m) => (
            <label key={m} className="flex items-center gap-1 cursor-pointer">
              <input
                type="radio"
                name="mode"
                value={m}
                checked={mode === m}
                onChange={() => setMode(m)}
                aria-checked={mode === m}
              />
              <span>{m === "text" ? "文本" : m === "file" ? "文件" : "URL"}</span>
            </label>
          ))}
        </div>
      </fieldset>

      <form onSubmit={onSubmit} className="space-y-4">
        {mode === "text" && (
          <label className="block">
            <span className="text-sm font-medium">测试需求 / 被测物描述</span>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              required
              rows={6}
              className="mt-1 w-full border rounded p-2 focus:ring-2 focus:ring-blue-500"
              placeholder="例:测试 Web 系统 https://example.com 的登录和支付流程"
              aria-required="true"
            />
          </label>
        )}
        {mode === "file" && (
          <label className="block">
            <span className="text-sm font-medium">上传被测物</span>
            <input
              type="file"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              required
              className="mt-1 block w-full"
              aria-required="true"
              accept=".pdf,.docx,.doc,.md,.txt,.apk,.ipa,.exe,.msi,.dmg,.tar,.zip,.json,.yaml"
            />
            <small className="text-xs text-slate-500">支持 PDF/Word/MD/APK/IPA/EXE/Docker 等</small>
          </label>
        )}
        {mode === "url" && (
          <label className="block">
            <span className="text-sm font-medium">被测 URL</span>
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              required
              placeholder="https://example.com"
              className="mt-1 w-full border rounded p-2 focus:ring-2 focus:ring-blue-500"
              aria-required="true"
            />
          </label>
        )}

        <label className="block">
          <span className="text-sm font-medium">补充提示(可选)</span>
          <input
            value={extra}
            onChange={(e) => setExtra(e.target.value)}
            className="mt-1 w-full border rounded p-2 focus:ring-2 focus:ring-blue-500"
            placeholder="例:重点测试 P0 路径 / 关注性能基线 / 等"
          />
        </label>

        <button
          type="submit"
          disabled={submit.isPending}
          className="px-4 py-2 bg-slate-900 text-white rounded disabled:opacity-50 focus:ring-2 focus:ring-blue-500"
          aria-busy={submit.isPending}
        >
          {submit.isPending ? "提交中..." : "开始测试"}
        </button>
        {submit.isError && (
          <p role="alert" className="text-red-600 text-sm">
            提交失败:{(submit.error as Error).message}
          </p>
        )}
      </form>
    </section>
  );
}
