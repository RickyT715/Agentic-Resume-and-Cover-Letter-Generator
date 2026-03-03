import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type {
  Task,
  Template,
  AppSettings,
  Prompts,
  EvaluationData,
  JDHistoryEntry,
} from '../types/task';

const API_URL = '/api';

async function fetchJSON<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

async function postJSON<T>(url: string, body?: unknown): Promise<T> {
  const res = await fetch(url, {
    method: 'POST',
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

async function putJSON<T>(url: string, body: unknown): Promise<T> {
  const res = await fetch(url, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

// ===== Queries =====

export function useTasksQuery() {
  return useQuery<Task[]>({
    queryKey: ['tasks'],
    queryFn: () => fetchJSON<Task[]>(`${API_URL}/tasks`),
    refetchInterval: 5000,
  });
}

export function useTaskQuery(taskId: string | undefined) {
  return useQuery<Task>({
    queryKey: ['task', taskId],
    queryFn: () => fetchJSON<Task>(`${API_URL}/tasks/${taskId}`),
    enabled: !!taskId,
    refetchInterval: 3000,
  });
}

export function useTemplatesQuery() {
  return useQuery<Template[]>({
    queryKey: ['templates'],
    queryFn: () => fetchJSON<Template[]>(`${API_URL}/templates`),
    staleTime: Infinity,
  });
}

export function useSettingsQuery() {
  return useQuery<AppSettings>({
    queryKey: ['settings'],
    queryFn: () => fetchJSON<AppSettings>(`${API_URL}/settings`),
  });
}

export function usePromptsQuery() {
  return useQuery<Prompts>({
    queryKey: ['prompts'],
    queryFn: () => fetchJSON<Prompts>(`${API_URL}/prompts`),
  });
}

export function useCoverLetterTextQuery(taskId: string | undefined, enabled: boolean) {
  return useQuery<{ text: string }>({
    queryKey: ['cover-letter-text', taskId],
    queryFn: () => fetchJSON<{ text: string }>(`${API_URL}/tasks/${taskId}/cover-letter-text`),
    enabled: !!taskId && enabled,
    staleTime: Infinity,
  });
}

export function useEvaluationQuery(taskId: string | undefined) {
  return useQuery<EvaluationData>({
    queryKey: ['evaluation', taskId],
    queryFn: () => fetchJSON<EvaluationData>(`${API_URL}/tasks/${taskId}/evaluation`),
    enabled: !!taskId,
    staleTime: 60000,
  });
}

export function useJdHistoryQuery(enabled: boolean) {
  return useQuery<JDHistoryEntry[]>({
    queryKey: ['jd-history'],
    queryFn: () => fetchJSON<JDHistoryEntry[]>(`${API_URL}/jd-history`),
    enabled,
    staleTime: 30000,
  });
}

// ===== Mutations =====

export function useCreateTaskMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: {
      job_description: string;
      generate_cover_letter?: boolean;
      template_id?: string;
      language?: string;
    }) => postJSON<Task>(`${API_URL}/tasks`, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tasks'] }),
  });
}

export function useStartTaskMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ taskId, pipeline }: { taskId: string; pipeline: 'v2' | 'v3' }) => {
      const endpoint = pipeline === 'v3' ? 'start-v3' : 'start';
      return postJSON<Task>(`${API_URL}/tasks/${taskId}/${endpoint}`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tasks'] }),
  });
}

export function useUpdateTaskSettingsMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ taskId, settings }: { taskId: string; settings: Record<string, unknown> }) =>
      putJSON<Task>(`${API_URL}/tasks/${taskId}/settings`, settings),
    onSuccess: (_, { taskId }) => {
      queryClient.invalidateQueries({ queryKey: ['task', taskId] });
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
  });
}

export function useRetryTaskMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (taskId: string) => postJSON<Task>(`${API_URL}/tasks/${taskId}/retry`),
    onSuccess: (_, taskId) => {
      queryClient.invalidateQueries({ queryKey: ['task', taskId] });
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
  });
}

export function useCancelTaskMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (taskId: string) => postJSON<Task>(`${API_URL}/tasks/${taskId}/cancel`),
    onSuccess: (_, taskId) => {
      queryClient.invalidateQueries({ queryKey: ['task', taskId] });
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
  });
}

export function useDeleteTaskMutation() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: async (taskId: string) => {
      const r = await fetch(`${API_URL}/tasks/${taskId}`, { method: 'DELETE' });
      if (!r.ok) throw new Error('Failed to delete task');
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tasks'] }),
  });
}

export function useEvaluateTaskMutation() {
  const queryClient = useQueryClient();
  return useMutation<EvaluationData, Error, string>({
    mutationFn: (taskId: string) => postJSON<EvaluationData>(`${API_URL}/tasks/${taskId}/evaluate`),
    onSuccess: (data, taskId) => {
      // Store the full response (including llm_breakdown) directly into cache.
      // Do NOT just invalidate — that triggers a GET refetch without llm_breakdown.
      queryClient.setQueryData(['evaluation', taskId], data);
    },
  });
}

export function useSaveSettingsMutation() {
  const queryClient = useQueryClient();
  return useMutation<AppSettings, Error, AppSettings>({
    mutationFn: (settings: AppSettings) => putJSON<AppSettings>(`${API_URL}/settings`, settings),
    onSuccess: (data) => {
      queryClient.setQueryData(['settings'], data);
    },
  });
}

export function useResetSettingsMutation() {
  const queryClient = useQueryClient();
  return useMutation<AppSettings, Error, void>({
    mutationFn: () => postJSON<AppSettings>(`${API_URL}/settings/reset`),
    onSuccess: (data) => {
      queryClient.setQueryData(['settings'], data);
    },
  });
}

export function useSavePromptMutation() {
  return useMutation<{ warnings?: string[] }, Error, { key: string; content: string }>({
    mutationFn: ({ key, content }) =>
      putJSON<{ warnings?: string[] }>(`${API_URL}/prompts/${key}`, { content }),
  });
}

export function useReloadPromptsMutation() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, void>({
    mutationFn: async () => {
      await postJSON<unknown>(`${API_URL}/prompts/reload`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prompts'] });
    },
  });
}

export function useScrapeCompanyMutation() {
  return useMutation<
    { chunks_indexed: number; pages_scraped: number },
    Error,
    { url: string; company_name: string }
  >({
    mutationFn: ({ url, company_name }) =>
      postJSON<{ chunks_indexed: number; pages_scraped: number }>(`${API_URL}/companies/scrape`, {
        url,
        company_name,
      }),
  });
}

export function useClearCompletedTasksMutation() {
  const queryClient = useQueryClient();
  return useMutation<{ count: number }, Error, void>({
    mutationFn: async () => {
      const r = await fetch(`${API_URL}/tasks`, { method: 'DELETE' });
      if (!r.ok) throw new Error('Failed to clear tasks');
      return r.json();
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tasks'] }),
  });
}
