// Renders the small Markdown subset used by reports and kept notes (headings, lists, rules,
// paragraphs, **bold**, _italic_, `code`, ``` fences) as React elements — never as raw HTML.
import { Fragment, type ReactNode } from "react";

function inline(text: string, key: string): ReactNode[] {
  const out: ReactNode[] = [];
  const re = /(\*\*[^*]+\*\*|`[^`]+`|(?<![\w])_[^_]+_(?![\w]))/g;
  let last = 0;
  let i = 0;
  for (const m of text.matchAll(re)) {
    if (m.index! > last) out.push(text.slice(last, m.index));
    const tok = m[0];
    const k = `${key}-${i++}`;
    if (tok.startsWith("**")) out.push(<strong key={k}>{tok.slice(2, -2)}</strong>);
    else if (tok.startsWith("`")) out.push(<code key={k} className="rounded bg-muted px-1 py-0.5 text-[0.85em]">{tok.slice(1, -1)}</code>);
    else out.push(<em key={k} className="text-muted-foreground">{tok.slice(1, -1)}</em>);
    last = m.index! + tok.length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

export function MarkdownView({ source, className }: { source: string; className?: string }) {
  const lines = source.replace(/\r\n/g, "\n").split("\n");
  const blocks: ReactNode[] = [];
  let list: string[] = [];
  let para: string[] = [];
  const flushList = () => {
    if (!list.length) return;
    const k = `l${blocks.length}`;
    blocks.push(<ul key={k} className="my-2 list-disc space-y-1 pl-6">{list.map((li, i) => <li key={i}>{inline(li, `${k}-${i}`)}</li>)}</ul>);
    list = [];
  };
  const flushPara = () => {
    if (!para.length) return;
    const k = `p${blocks.length}`;
    blocks.push(<p key={k} className="my-2">{inline(para.join(" "), k)}</p>);
    para = [];
  };
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (line.startsWith("```")) {
      flushList(); flushPara();
      const code: string[] = [];
      for (i++; i < lines.length && !lines[i].startsWith("```"); i++) code.push(lines[i]);
      blocks.push(<pre key={`c${blocks.length}`} className="my-3 overflow-x-auto rounded-md bg-muted p-3 text-xs"><code>{code.join("\n")}</code></pre>);
      continue;
    }
    const h = line.match(/^(#{1,3})\s+(.*)$/);
    if (h) {
      flushList(); flushPara();
      const k = `h${blocks.length}`;
      const cls = h[1].length === 1 ? "mt-1 mb-3 text-xl font-semibold" : h[1].length === 2 ? "mt-6 mb-2 border-b pb-1 text-base font-semibold" : "mt-4 mb-1 text-sm font-semibold text-muted-foreground";
      const Tag = (`h${h[1].length + 1}`) as "h2" | "h3" | "h4";
      blocks.push(<Tag key={k} className={cls}>{inline(h[2], k)}</Tag>);
      continue;
    }
    if (/^\s*---+\s*$/.test(line)) { flushList(); flushPara(); blocks.push(<hr key={`r${blocks.length}`} className="my-4" />); continue; }
    const li = line.match(/^\s*[-*]\s+(.*)$/);
    if (li) { flushPara(); list.push(li[1]); continue; }
    if (!line.trim()) { flushList(); flushPara(); continue; }
    if (list.length && /^\s{2,}/.test(line)) { list[list.length - 1] += " " + line.trim(); continue; }
    flushList();
    para.push(line.trim());
  }
  flushList(); flushPara();
  return <div className={className}><Fragment>{blocks}</Fragment></div>;
}
