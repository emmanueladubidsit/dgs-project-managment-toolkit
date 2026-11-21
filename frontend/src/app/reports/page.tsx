"use client";
import { PageHeader } from "@/components/common";
import { ReportComposer } from "@/components/report-composer";

export default function ReportsPage() {
  return (
    <>
      <PageHeader title="Reports" description="Daily, weekly and project reports generated from what is actually recorded. Edit, copy, download or save them." />
      <ReportComposer />
    </>
  );
}
