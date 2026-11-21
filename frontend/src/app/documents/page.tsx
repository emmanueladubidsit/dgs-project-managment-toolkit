"use client";
import { useState } from "react";
import { PageHeader } from "@/components/common";
import { DocumentsList, FoldersPanel } from "@/components/documents";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default function DocumentsPage() {
  const [tab, setTab] = useState("documents");
  return (
    <>
      <PageHeader title="Documents & Artefacts" description="Briefs, architecture, ADRs, diagrams, reports and more — indexed where they already live." />
      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="mb-4">
          <TabsTrigger value="documents">Documents</TabsTrigger>
          <TabsTrigger value="folders">Folders</TabsTrigger>
        </TabsList>
        <TabsContent value="documents"><DocumentsList /></TabsContent>
        <TabsContent value="folders"><FoldersPanel /></TabsContent>
      </Tabs>
    </>
  );
}
