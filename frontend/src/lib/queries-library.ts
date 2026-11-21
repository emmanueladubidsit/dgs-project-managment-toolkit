"use client";
// Data hooks for Knowledge, Methodologies, Documents and Voice.
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api, errorMessage } from "./api";
import { useAction } from "./queries";
import type {
  ClaudeSetup, CodeEvent, Connection, Adoption, CategoryTemplate, DocumentRoot, KnowledgeDetail, KnowledgeItem, KnowledgeVersion, MethodologyDetail,
  MethodologySummary, ProjectDeliverable, ProjectDocument, ScannedFile, SearchHit, Suggestion, VoiceNote, VoiceStatus,
} from "./types";

type Q = Record<string, string | boolean | string[] | undefined>;

// ---------------------------------------------------------------- search
export const useSearch = (q: string) =>
  useQuery({ queryKey: ["search", q], queryFn: () => api<SearchHit[]>("/search", { query: { q } }), enabled: q.trim().length >= 2 });

// ---------------------------------------------------------------- knowledge
export const useKnowledgeTemplates = () =>
  useQuery({ queryKey: ["knowledge-templates"], queryFn: () => api<CategoryTemplate[]>("/knowledge/templates"), staleTime: Infinity });
export const useKnowledgeList = (query: Q = {}) =>
  useQuery({ queryKey: ["knowledge", query], queryFn: () => api<KnowledgeItem[]>("/knowledge", { query }) });
export const useKnowledge = (id: string) =>
  useQuery({ queryKey: ["knowledge-item", id], queryFn: () => api<KnowledgeDetail>(`/knowledge/${id}`) });
export const useKnowledgeVersions = (id: string) =>
  useQuery({ queryKey: ["knowledge-versions", id], queryFn: () => api<KnowledgeVersion[]>(`/knowledge/${id}/versions`) });

type KInput = Partial<Omit<KnowledgeItem, "id" | "projects">> & { origin_project_id?: string | null; change_note?: string };
export const useCreateKnowledge = () =>
  useAction((body: KInput) => api<KnowledgeDetail>("/knowledge", { method: "POST", body }), { success: "Knowledge saved." });
export const useUpdateKnowledge = (id: string) =>
  useAction((body: KInput) => api<KnowledgeDetail>(`/knowledge/${id}`, { method: "PATCH", body }), { success: "Knowledge saved." });
export const useKnowledgeAction = (id: string) =>
  useAction(({ path, method = "POST", body, query }: { path: string; method?: string; body?: unknown; query?: Q }) =>
    api<KnowledgeDetail>(`/knowledge/${id}${path}`, { method, body, query: query as never }));
export const useDeleteKnowledge = () =>
  useAction((id: string) => api<void>(`/knowledge/${id}`, { method: "DELETE", query: { confirm: true } }), { success: "Knowledge deleted." });
export const useDeleteRelation = () =>
  useAction((id: string) => api<void>(`/knowledge/relations/${id}`, { method: "DELETE" }));
export const usePromoteWorkLog = () =>
  useAction((logId: string) => api<KnowledgeDetail>(`/knowledge/from-work-log/${logId}`, { method: "POST" }),
    { success: "Saved to Knowledge & Research as a draft." });

// ---------------------------------------------------------------- methodologies
export const useMethodologies = (query: Q = {}) =>
  useQuery({ queryKey: ["methodologies", query], queryFn: () => api<MethodologySummary[]>("/methodologies", { query }) });
export const useMethodology = (id: string) =>
  useQuery({ queryKey: ["methodology", id], queryFn: () => api<MethodologyDetail>(`/methodologies/${id}`), enabled: !!id });
export const useMethodologyVersions = (id: string) =>
  useQuery({ queryKey: ["methodology-versions", id], queryFn: () => api<KnowledgeVersion[]>(`/methodologies/${id}/versions`) });
export const useCreateMethodology = () =>
  useAction((body: Record<string, unknown>) => api<MethodologyDetail>("/methodologies", { method: "POST", body }), { success: "Methodology created." });
export const useMethodologyAction = (id: string) =>
  useAction(({ path = "", method = "POST", body, query, success }: { path?: string; method?: string; body?: unknown; query?: Q; success?: string }) =>
    api<MethodologyDetail>(`/methodologies/${id}${path}`, { method, body, query: query as never }).then((r) => {
      if (success) toast.success(success);
      return r;
    }));
export const useFromProject = () =>
  useAction(({ projectId, ...body }: { projectId: string; name: string; kind: string }) =>
    api<MethodologyDetail>(`/methodologies/from-project/${projectId}`, { method: "POST", body }), { success: "Draft created from the project." });
export const useAdoptions = (projectId: string) =>
  useQuery({ queryKey: ["adoptions", projectId], queryFn: () => api<Adoption[]>(`/projects/${projectId}/methodologies`) });
export const useAdopt = () =>
  useAction(({ projectId, ...body }: { projectId: string; methodology_id: string; stage_ids: string[] | null; create_milestones: boolean; create_tasks: boolean; start_date: string | null }) =>
    api<Adoption>(`/projects/${projectId}/methodologies`, { method: "POST", body }),
    { success: (a) => `Adopted: ${a.milestones_created} milestone(s) and ${a.tasks_created} task(s) created.` });
export const useUpdateProjectDeliverable = () =>
  useAction(({ id, ...body }: Partial<ProjectDeliverable> & { id: string }) =>
    api<ProjectDeliverable>(`/project-deliverables/${id}`, { method: "PATCH", body }));
export const useRemoveAdoption = () =>
  useAction((id: string) => api<void>(`/project-methodologies/${id}`, { method: "DELETE" }), { success: "Adoption removed. Its tasks were kept." });

// ---------------------------------------------------------------- documents
export const useDocumentRoots = () => useQuery({ queryKey: ["document-roots"], queryFn: () => api<DocumentRoot[]>("/document-roots") });
export const useDocuments = (query: Q = {}) =>
  useQuery({ queryKey: ["documents", query], queryFn: () => api<ProjectDocument[]>("/documents", { query }) });
export const useDocument = (id: string | null) =>
  useQuery({ queryKey: ["document", id], queryFn: () => api<ProjectDocument>(`/documents/${id}`), enabled: !!id });
export const usePreview = (id: string | null, enabled: boolean) =>
  useQuery({ queryKey: ["preview", id], queryFn: () => api<{ text: string }>(`/documents/${id}/preview`), enabled: !!id && enabled, retry: false });
export const useRegisterRoot = () =>
  useAction((body: { name: string; path: string; project_id: string | null }) => api<DocumentRoot>("/document-roots", { method: "POST", body }),
    { success: "Folder registered (read-only)." });
export const useRemoveRoot = () =>
  useAction((id: string) => api<void>(`/document-roots/${id}`, { method: "DELETE", query: { confirm: true } }),
    { success: "Folder removed from the index. Your files were not touched." });
export function useScan() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (rootId: string) => api<{ files: ScannedFile[]; truncated: boolean; skipped_note: string }>(`/document-roots/${rootId}/scan`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["document-roots"] }),
    onError: (e) => toast.error(errorMessage(e)),
  });
}
export const useRegisterFiles = () =>
  useAction(({ rootId, ...body }: { rootId: string; paths: string[]; project_id: string | null }) =>
    api<ProjectDocument[]>(`/document-roots/${rootId}/register`, { method: "POST", body }),
    { success: (r) => `${r.length} document(s) indexed.` });
export const useCreateDocument = () =>
  useAction((body: Partial<ProjectDocument>) => api<ProjectDocument>("/documents", { method: "POST", body }), { success: "Document added." });
export const useUpdateDocument = () =>
  useAction(({ id, ...body }: Partial<ProjectDocument> & { id: string }) => api<ProjectDocument>(`/documents/${id}`, { method: "PATCH", body }), { success: "Document saved." });
export const useDocumentAction = () =>
  useAction(({ id, path, method = "POST", body }: { id: string; path: string; method?: string; body?: unknown }) =>
    api<ProjectDocument>(`/documents/${id}${path}`, { method, body }));
export const useDeleteDocument = () =>
  useAction((id: string) => api<void>(`/documents/${id}`, { method: "DELETE" }), { success: "Record removed. The file itself was not touched." });

// ---------------------------------------------------------------- voice
export const useVoiceStatus = () => useQuery({ queryKey: ["voice-status"], queryFn: () => api<VoiceStatus>("/voice/status") });
export const useVoiceNotes = () => useQuery({ queryKey: ["voice-notes"], queryFn: () => api<VoiceNote[]>("/voice/notes") });
export const useVoiceNote = (id: string) => useQuery({ queryKey: ["voice-note", id], queryFn: () => api<VoiceNote>(`/voice/notes/${id}`) });
export const useSuggestions = (query: Q) =>
  useQuery({ queryKey: ["suggestions", query], queryFn: () => api<Suggestion[]>("/suggestions", { query }) });

export function useUploadRecording() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ blob, title, projectId }: { blob: Blob; title: string; projectId: string | null }) => {
      const form = new FormData();
      const ext = blob.type.includes("mp4") ? "m4a" : blob.type.includes("ogg") ? "ogg" : "webm";
      form.append("audio", blob, `recording.${ext}`);
      form.append("title", title);
      if (projectId) form.append("project_id", projectId);
      const res = await fetch("/api/voice/notes", { method: "POST", body: form });
      const data = await res.json().catch(() => null);
      if (!res.ok) throw new Error(data?.error?.message ?? "The recording could not be uploaded.");
      return data as VoiceNote;
    },
    onSuccess: () => { qc.invalidateQueries(); toast.success("Transcribed."); },
    onError: (e) => toast.error(errorMessage(e)),
  });
}
export const useCreateTextNote = () =>
  useAction((body: { title: string; text: string; project_id: string | null }) => api<VoiceNote>("/voice/notes/text", { method: "POST", body }), { success: "Note saved." });
export const useUpdateVoiceNote = (id: string) =>
  useAction((body: Partial<VoiceNote>) => api<VoiceNote>(`/voice/notes/${id}`, { method: "PATCH", body }), { success: "Saved." });
export const useDeleteVoiceNote = () =>
  useAction((id: string) => api<void>(`/voice/notes/${id}`, { method: "DELETE" }), { success: "Note deleted." });
export const useDeleteAudio = (id: string) =>
  useAction(() => api<VoiceNote>(`/voice/notes/${id}/audio`, { method: "DELETE" }), { success: "Recording deleted." });
export const useTransform = (id: string) =>
  useMutation({
    mutationFn: (body: { output: string; text?: string }) =>
      api<{ output: string; label: string; text: string | null; needs_ai: boolean; message: string | null }>(`/voice/notes/${id}/transform`, { method: "POST", body }),
    onError: (e) => toast.error(errorMessage(e)),
  });
export const useSaveAsUpdate = (id: string) =>
  useAction((body: { kind: string; entry_date: string; text: string }) => api<{ work_log_id: string }>(`/voice/notes/${id}/save-as-update`, { method: "POST", body }),
    { success: "Recorded as an update." });
export const useExtractSuggestions = (id: string) =>
  useAction(() => api<Suggestion[]>(`/voice/notes/${id}/suggestions`, { method: "POST" }),
    { success: (r) => (r.length ? `${r.length} suggestion(s) to review.` : "No new suggestions found.") });
export const useSuggestionAction = () =>
  useAction(({ id, action, body }: { id: string; action: "approve" | "reject" | "defer" | "edit"; body?: unknown }) =>
    action === "edit"
      ? api<Suggestion>(`/suggestions/${id}`, { method: "PATCH", body })
      : api<Suggestion>(`/suggestions/${id}/${action}`, { method: "POST", body: body ?? {} }));

// ---------------------------------------------------------------- connected codebases & Claude
export const useConnection = (projectId: string) =>
  useQuery({ queryKey: ["connection", projectId], queryFn: () => api<Connection | null>(`/projects/${projectId}/connection`) });
export const useCodeEvents = (projectId: string, enabled: boolean) =>
  useQuery({ queryKey: ["code-events", projectId], queryFn: () => api<CodeEvent[]>(`/projects/${projectId}/code-events`), enabled, refetchInterval: 30_000 });
export const useConnect = (projectId: string) =>
  useAction((body: { path: string; accept_claude: boolean; auto_sync: boolean; progress_patterns?: string[] }) =>
    api<Connection>(`/projects/${projectId}/connection`, { method: "PUT", body }), { success: "Folder connected and synced (read-only)." });
export const useDisconnect = (projectId: string) =>
  useAction(() => api<void>(`/projects/${projectId}/connection`, { method: "DELETE" }), { success: "Folder disconnected. Your files were not touched." });
export const useSyncNow = (projectId: string) =>
  useAction(() => api<{ new_commits: number; suggestions: number; uncommitted_changes: number; files_changed: number }>(`/projects/${projectId}/sync`, { method: "POST" }),
    { success: (r) => `Synced: ${r.new_commits} new commit(s), ${r.suggestions} suggestion(s).` });
export const useSaveEventAsUpdate = () =>
  useAction((id: string) => api<{ work_log_id: string }>(`/code-events/${id}/save-as-update`, { method: "POST" }), { success: "Recorded as a progress update." });
export const useClaudeSettings = () => useQuery({ queryKey: ["claude-settings"], queryFn: () => api<{ allow_outbound: boolean }>("/claude/settings") });
export const useSaveClaudeSettings = () =>
  useAction((body: { allow_outbound: boolean }) => api<{ allow_outbound: boolean }>("/claude/settings", { method: "PUT", body }),
    { success: (r) => (r.allow_outbound ? "Claude Code may now read workspace tasks." : "Workspace tasks are no longer shared with Claude Code.") });
export const useClaudeSetup = () => useQuery({ queryKey: ["claude-setup"], queryFn: () => api<ClaudeSetup>("/claude/setup"), staleTime: Infinity });
export const usePrivacyNames = () => useQuery({ queryKey: ["privacy-names"], queryFn: () => api<{ name: string; replacement: string }[]>("/privacy/names") });
export const useSavePrivacyNames = () =>
  useAction((body: { name: string; replacement: string }[]) => api<unknown>("/privacy/names", { method: "PUT", body }), { success: "Privacy rules saved." });
