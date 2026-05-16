import { useState, FormEvent } from "react";
import { MessageSquare, Send, Check, AlertCircle } from "lucide-react";

const MODULES = [
  "Upload / Run",
  "Report / Results",
  "Catalog / Skills",
  "Settings / Config",
  "Doctor / Check",
  "CLI / tagent",
  "Desktop App",
  "Install / Setup",
  "Documentation",
  "Expert (specify)",
  "Skill (specify)",
  "Other",
];

const TYPES = ["Bug Report", "Feature Request", "Question", "Feedback"];

interface FeedbackEntry {
  id: string;
  type: string;
  module: string;
  title: string;
  description: string;
  email: string;
  timestamp: string;
}

function saveFeedback(entry: FeedbackEntry) {
  const existing = JSON.parse(localStorage.getItem("tagent_feedback") || "[]");
  existing.push(entry);
  localStorage.setItem("tagent_feedback", JSON.stringify(existing));
}

export default function FeedbackPage() {
  const [type, setType] = useState("Bug Report");
  const [module, setModule] = useState("");
  const [title, setTitle] = useState("");
  const [desc, setDesc] = useState("");
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!module || !title || !desc) {
      setError("Please fill in module, title, and description.");
      return;
    }

    const entry: FeedbackEntry = {
      id: `fb-${Date.now()}`,
      type,
      module,
      title,
      description: desc,
      email,
      timestamp: new Date().toISOString(),
    };

    saveFeedback(entry);

    // Also try to submit to GitHub Issues if in desktop app
    if ((window as any).electronAPI?.isElectron) {
      try {
        const body = `## ${type}: ${title}\n\n**Module**: ${module}\n**Email**: ${email || "N/A"}\n\n### Description\n${desc}\n\n---\n*Submitted via Test-Agent Desktop v1.32.0*`;
        fetch("http://localhost:8800/feedback", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ type, module, title, body }),
        }).catch(() => {});
      } catch {}
    }

    setSent(true);
    setError("");
  };

  if (sent) {
    return (
      <div className="max-w-2xl mx-auto p-6 text-center space-y-4">
        <Check className="w-12 h-12 text-green-500 mx-auto" />
        <h2 className="text-xl font-semibold">Thank you!</h2>
        <p className="text-slate-600">Your feedback has been saved. We review every submission.</p>
        <button onClick={() => { setSent(false); setTitle(""); setDesc(""); setModule(""); }} className="text-blue-600 hover:underline text-sm">
          Submit another
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto p-6 space-y-6">
      <h2 className="text-xl font-semibold flex items-center gap-2">
        <MessageSquare className="w-5 h-5" /> Feedback
      </h2>

      {error && (
        <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          <AlertCircle className="w-4 h-4" /> {error}
        </div>
      )}

      <form onSubmit={submit} className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <section className="space-y-2">
            <label className="text-sm font-medium text-slate-600">Type</label>
            <div className="grid grid-cols-2 gap-1.5">
              {TYPES.map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setType(t)}
                  className={`text-left px-3 py-1.5 rounded-lg border text-xs transition
                    ${type === t ? "border-blue-500 bg-blue-50 ring-1 ring-blue-500" : "border-slate-200 hover:border-slate-300"}`}
                >
                  {t}
                </button>
              ))}
            </div>
          </section>

          <section className="space-y-2">
            <label className="text-sm font-medium text-slate-600">Module</label>
            <select
              value={module}
              onChange={(e) => setModule(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg text-sm"
              required
            >
              <option value="" disabled>Select module...</option>
              {MODULES.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </section>
        </div>

        <section className="space-y-2">
          <label className="text-sm font-medium text-slate-600">Title</label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Brief summary of the issue or suggestion"
            className="w-full px-3 py-2 border rounded-lg text-sm"
            required
          />
        </section>

        <section className="space-y-2">
          <label className="text-sm font-medium text-slate-600">Description</label>
          <textarea
            value={desc}
            onChange={(e) => setDesc(e.target.value)}
            placeholder="Steps to reproduce, expected vs actual behavior, screenshots..."
            rows={5}
            className="w-full px-3 py-2 border rounded-lg text-sm resize-y"
            required
          />
        </section>

        <section className="space-y-2">
          <label className="text-sm font-medium text-slate-600">
            Email <span className="text-slate-400 font-normal">(optional — we'll reply if needed)</span>
          </label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="w-full px-3 py-2 border rounded-lg text-sm"
          />
        </section>

        <button
          type="submit"
          className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition text-sm"
        >
          <Send className="w-4 h-4" /> Submit Feedback
        </button>
      </form>

      <p className="text-xs text-slate-400">
        Feedback is stored locally and reviewed regularly.
        For urgent issues, open a{" "}
        <a href="https://github.com/Wool-xing/Test-Agent/issues/new" target="_blank" rel="noopener" className="text-blue-600 hover:underline">
          GitHub Issue
        </a>.
      </p>
    </div>
  );
}
