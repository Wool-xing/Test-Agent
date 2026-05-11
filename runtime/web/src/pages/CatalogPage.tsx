import { useQuery } from "@tanstack/react-query";
import { getCatalog } from "@/api";

export default function CatalogPage() {
  const query = useQuery({ queryKey: ["catalog"], queryFn: getCatalog });

  if (query.isLoading) return <p>加载中...</p>;
  if (query.isError)
    return (
      <p role="alert" className="text-red-600">
        加载失败:{(query.error as Error).message}
      </p>
    );

  const data = query.data!;
  return (
    <section aria-labelledby="catalog-heading" className="max-w-4xl">
      <h2 id="catalog-heading" className="text-2xl font-bold mb-2">
        Catalog
      </h2>
      <p className="text-sm text-slate-600 mb-6">
        {data.counts.experts} 专家 + {data.counts.skills} 技能 · 由 `02-专家定义/` + `03-技能定义/`
        frontmatter 自动加载
      </p>

      <section className="mb-8" aria-labelledby="experts-heading">
        <h3 id="experts-heading" className="text-lg font-semibold mb-2">
          专家 ({data.counts.experts})
        </h3>
        <ul className="space-y-2">
          {data.experts.map((e) => (
            <li key={e.name} className="border rounded p-3">
              <code className="text-blue-600 font-medium">{e.name}</code>
              <p className="text-sm text-slate-700 mt-1">{e.description}</p>
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="skills-heading">
        <h3 id="skills-heading" className="text-lg font-semibold mb-2">
          技能 ({data.counts.skills})
        </h3>
        <ul className="space-y-2">
          {data.skills.map((s) => (
            <li key={s.name} className="border rounded p-3">
              <code className="text-blue-600 font-medium">/{s.name}</code>
              <p className="text-sm text-slate-700 mt-1">{s.description}</p>
            </li>
          ))}
        </ul>
      </section>
    </section>
  );
}
