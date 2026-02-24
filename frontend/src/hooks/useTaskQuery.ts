import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import type { Task, Template } from "../types/task"

const API_URL = "/api"

async function fetchJSON<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data.detail || `Request failed: ${res.status}`)
  }
  return res.json()
}

async function postJSON<T>(url: string, body?: unknown): Promise<T> {
  const res = await fetch(url, {
    method: "POST",
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data.detail || `Request failed: ${res.status}`)
  }
  return res.json()
}

async function putJSON<T>(url: string, body: unknown): Promise<T> {
  const res = await fetch(url, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data.detail || `Request failed: ${res.status}`)
  }
  return res.json()
}

// ===== Queries =====

export function useTasksQuery() {
  return useQuery<Task[]>({
    queryKey: ["tasks"],
    queryFn: () => fetchJSON<Task[]>(`${API_URL}/tasks`),
    refetchInterval: 5000,
  })
}

export function useTaskQuery(taskId: string | undefined) {
  return useQuery<Task>({
    queryKey: ["task", taskId],
    queryFn: () => fetchJSON<Task>(`${API_URL}/tasks/${taskId}`),
    enabled: !!taskId,
    refetchInterval: 3000,
  })
}

export function useTemplatesQuery() {
  return useQuery<Template[]>({
    queryKey: ["templates"],
    queryFn: () => fetchJSON<Template[]>(`${API_URL}/templates`),
    staleTime: Infinity,
  })
}

export function useSettingsQuery() {
  return useQuery({
    queryKey: ["settings"],
    queryFn: () => fetchJSON(`${API_URL}/settings`),
  })
}

export function usePromptsQuery() {
  return useQuery({
    queryKey: ["prompts"],
    queryFn: () => fetchJSON(`${API_URL}/prompts`),
  })
}

export function useEvaluationQuery(taskId: string | undefined) {
  return useQuery({
    queryKey: ["evaluation", taskId],
    queryFn: () => fetchJSON(`${API_URL}/tasks/${taskId}/evaluation`),
    enabled: !!taskId,
    staleTime: 60000,
  })
}

// ===== Mutations =====

export function useCreateTaskMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: { job_description: string; generate_cover_letter?: boolean; template_id?: string; language?: string }) =>
      postJSON<Task>(`${API_URL}/tasks`, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["tasks"] }),
  })
}

export function useStartTaskMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ taskId, pipeline }: { taskId: string; pipeline: "v2" | "v3" }) => {
      const endpoint = pipeline === "v3" ? "start-v3" : "start"
      return postJSON(`${API_URL}/tasks/${taskId}/${endpoint}`)
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["tasks"] }),
  })
}

export function useUpdateTaskSettingsMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ taskId, settings }: { taskId: string; settings: Record<string, unknown> }) =>
      putJSON<Task>(`${API_URL}/tasks/${taskId}/settings`, settings),
    onSuccess: (_, { taskId }) => {
      queryClient.invalidateQueries({ queryKey: ["task", taskId] })
      queryClient.invalidateQueries({ queryKey: ["tasks"] })
    },
  })
}

export function useRetryTaskMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (taskId: string) => postJSON<Task>(`${API_URL}/tasks/${taskId}/retry`),
    onSuccess: (_, taskId) => {
      queryClient.invalidateQueries({ queryKey: ["task", taskId] })
      queryClient.invalidateQueries({ queryKey: ["tasks"] })
    },
  })
}

export function useCancelTaskMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (taskId: string) => postJSON<Task>(`${API_URL}/tasks/${taskId}/cancel`),
    onSuccess: (_, taskId) => {
      queryClient.invalidateQueries({ queryKey: ["task", taskId] })
      queryClient.invalidateQueries({ queryKey: ["tasks"] })
    },
  })
}

export function useDeleteTaskMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (taskId: string) =>
      fetch(`${API_URL}/tasks/${taskId}`, { method: "DELETE" }).then((r) => {
        if (!r.ok) throw new Error("Failed to delete task")
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["tasks"] }),
  })
}

export function useEvaluateTaskMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (taskId: string) => postJSON(`${API_URL}/tasks/${taskId}/evaluate`),
    onSuccess: (_, taskId) => {
      queryClient.invalidateQueries({ queryKey: ["evaluation", taskId] })
    },
  })
}
