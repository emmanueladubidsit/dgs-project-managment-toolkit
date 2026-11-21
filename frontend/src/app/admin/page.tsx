"use client";
import { AISettings } from "@/components/ai-settings";
import { ClaudeSetupPanel, PrivacyPanel } from "@/components/codebase";
import { PageHeader, QueryView, Section } from "@/components/common";
import { useHealth, useSystemInfo } from "@/lib/queries";

type Info = {
  app_name: string; version: string;
  database: { engine: string; migration: string; size: string };
  record_counts: Record<string, number>;
  integrations: Record<string, string>;
};

export default function AdminPage() {
  const health = useHealth();
  const info = useSystemInfo();
  return (
    <>
      <PageHeader title="Administration" description="System health and diagnostics. Contains no secrets or credentials." />
      <div className="grid gap-4 md:grid-cols-2">
        <Section title="Health">
          <QueryView query={health}>
            {(h) => (
              <dl className="space-y-1 text-sm">
                <Row k="Overall status" v={h.status === "ok" ? "Healthy" : "Degraded"} />
                <Row k="Database" v={h.database === "ok" ? "Connected" : "Unavailable"} />
                <Row k="API version" v={h.version} />
              </dl>
            )}
          </QueryView>
        </Section>
        <QueryView query={info}>
          {(raw) => {
            const i = raw as unknown as Info;
            return (
              <>
                <Section title="Database">
                  <dl className="space-y-1 text-sm">
                    <Row k="Engine" v={i.database.engine} />
                    <Row k="Schema migration" v={i.database.migration} />
                    <Row k="Size on disk" v={i.database.size} />
                  </dl>
                </Section>
                <Section title="Records">
                  <dl className="space-y-1 text-sm">{Object.entries(i.record_counts).map(([k, v]) => <Row key={k} k={k.replace("_", " ")} v={String(v)} />)}</dl>
                </Section>
                <Section title="Integrations">
                  <dl className="space-y-1 text-sm">{Object.entries(i.integrations).map(([k, v]) => <Row key={k} k={k.replace("_", " ")} v={v} />)}</dl>
                  <p className="mt-2 text-xs text-muted-foreground">All integrations are optional; the workspace works fully without them.</p>
                </Section>
              </>
            );
          }}
        </QueryView>
        <AISettings />
        <ClaudeSetupPanel />
        <PrivacyPanel />
        <Section title="Backups" className="md:col-span-2">
          <p className="text-sm">Back up the database from a terminal in the project folder:</p>
          <pre className="mt-2 overflow-x-auto rounded-md bg-muted p-3 text-xs">docker exec dgs-workspace-db pg_dump -U dgs -Fc dgs_workspace &gt; backups/workspace-$(date +%F).dump</pre>
          <p className="mt-2 text-xs text-muted-foreground">See docs/DEVELOPMENT_SETUP.md for restore instructions. Backups are git-ignored and must never be committed.</p>
        </Section>
      </div>
    </>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return <div className="flex justify-between gap-4"><dt className="text-muted-foreground capitalize">{k}</dt><dd className="text-right font-medium">{v}</dd></div>;
}
