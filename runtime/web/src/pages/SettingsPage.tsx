import { useState } from "react";
import { Settings, Key, Cpu, Save, Check } from "lucide-react";

const PROVIDERS = [
  { id: "claude", label: "Claude (Anthropic)", models: ["claude-sonnet-4-6", "claude-opus-4-7", "claude-haiku-4-5"] },
  { id: "openai", label: "OpenAI", models: ["gpt-4o", "gpt-4o-mini"] },
  { id: "deepseek", label: "DeepSeek", models: ["deepseek-chat", "deepseek-reasoner"] },
  { id: "qwen", label: "Qwen", models: ["qwen-plus", "qwen-max"] },
  { id: "gemini", label: "Gemini (Google)", models: ["gemini-2.5-pro", "gemini-2.5-flash"] },
  { id: "ollama", label: "Ollama (Local)", models: ["qwen2.5:7b", "llama3.2:3b"] },
  { id: "stub", label: "Stub (Offline/Demo)", models: ["stub"] },
];

export default function SettingsPage() {
  const [provider, setProvider] = useState(localStorage.getItem("tagent_provider") || "stub");
  const [apiKey, setApiKey] = useState("");  // 安全: 不持久化, 仅 in-memory; 刷新后重输
  const [model, setModel] = useState(localStorage.getItem("tagent_model") || "stub");
  const [saved, setSaved] = useState(false);

  const currentProvider = PROVIDERS.find((p) => p.id === provider)!;

  const save = () => {
    localStorage.setItem("tagent_provider", provider);
    localStorage.setItem("tagent_model", model);
    // apiKey 不写 localStorage; 仅当前会话 in-memory state (防 XSS 读取)
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="max-w-2xl mx-auto p-6 space-y-6">
      <h2 className="text-xl font-semibold flex items-center gap-2">
        <Settings className="w-5 h-5" /> Settings
      </h2>

      {/* LLM Provider */}
      <section className="space-y-3">
        <h3 className="text-sm font-medium flex items-center gap-1.5 text-slate-600">
          <Cpu className="w-4 h-4" /> LLM Provider
        </h3>
        <div className="grid grid-cols-2 gap-2">
          {PROVIDERS.map((p) => (
            <button
              key={p.id}
              onClick={() => { setProvider(p.id); setModel(p.models[0]); }}
              className={`text-left px-3 py-2 rounded-lg border text-sm transition
                ${provider === p.id ? "border-blue-500 bg-blue-50 ring-1 ring-blue-500" : "border-slate-200 hover:border-slate-300"}`}
            >
              <div className="font-medium">{p.label}</div>
              <div className="text-xs text-slate-400">{p.models.length} models</div>
            </button>
          ))}
        </div>
      </section>

      {/* API Key */}
      <section className="space-y-2">
        <h3 className="text-sm font-medium flex items-center gap-1.5 text-slate-600">
          <Key className="w-4 h-4" /> API Key {provider === "stub" || provider === "ollama" ? "(optional)" : ""}
        </h3>
        <input
          type="password"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          placeholder={provider === "stub" ? "No key needed (offline demo)" : "sk-..."}
          className="w-full px-3 py-2 border rounded-lg text-sm font-mono"
          disabled={provider === "stub"}
        />
      </section>

      {/* Model */}
      <section className="space-y-2">
        <h3 className="text-sm font-medium text-slate-600">Model</h3>
        <select
          value={model}
          onChange={(e) => setModel(e.target.value)}
          className="w-full px-3 py-2 border rounded-lg text-sm"
        >
          {currentProvider.models.map((m) => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
      </section>

      {/* Save */}
      <button
        onClick={save}
        className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition text-sm"
      >
        {saved ? <Check className="w-4 h-4" /> : <Save className="w-4 h-4" />}
        {saved ? "Saved" : "Save Settings"}
      </button>

      <p className="text-xs text-slate-400">
        Provider 与 model 本地保存。<strong>API key 仅在当前会话有效</strong>(出于安全考虑不持久化,刷新页面或重启后需重输)。{provider === "stub" ? "Stub 模式无需 key,用于离线 demo。" : ""}
      </p>
    </div>
  );
}
