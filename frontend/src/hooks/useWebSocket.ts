import { useEffect, useRef, useCallback, useState } from 'react';
import { useTaskStore } from '../store/taskStore';
import { WebSocketMessage } from '../types/task';

const getWsUrl = () => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.hostname;
  const port = import.meta.env.DEV ? (import.meta.env.VITE_BACKEND_PORT || '48765') : window.location.port;
  return `${protocol}//${host}:${port}/ws`;
};

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const updateTaskProgress = useTaskStore((state) => state.updateTaskProgress);
  const updateTask = useTaskStore((state) => state.updateTask);
  const addToast = useTaskStore((state) => state.addToast);

  const fetchTaskDetails = useCallback(
    async (taskId: string) => {
      try {
        const response = await fetch(`/api/tasks/${taskId}`);
        if (response.ok) {
          const task = await response.json();
          updateTask(taskId, task);
        }
      } catch (e) {
        console.error('Failed to fetch task details:', e);
      }
    },
    [updateTask]
  );

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const wsUrl = getWsUrl();

    try {
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);

          if (message.type === 'progress') {
            const update = message.data;
            updateTaskProgress(update);

            // Fetch full task details on terminal states
            if (update.status === 'completed' || update.status === 'failed' || update.status === 'cancelled') {
              // Check if this is the last step completion or any failure/cancel
              const isTerminal =
                update.status === 'failed' ||
                update.status === 'cancelled' ||
                update.step === 'create_cover_pdf' ||
                update.step === 'compile_latex';

              if (isTerminal) {
                fetchTaskDetails(update.task_id);

                // Show toast notification
                if (update.status === 'completed') {
                  addToast('success', `Task ${update.task_number} completed successfully`);
                } else if (update.status === 'failed') {
                  addToast('error', `Task ${update.task_number} failed`);
                } else if (update.status === 'cancelled') {
                  addToast('info', `Task ${update.task_number} cancelled`);
                }
              }
            }
          }
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
        }
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setIsConnected(false);
        wsRef.current = null;

        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
        }
        reconnectTimeoutRef.current = window.setTimeout(() => {
          connect();
        }, 3000);
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setIsConnected(false);
      };

      wsRef.current = ws;
    } catch (e) {
      console.error('Failed to create WebSocket:', e);
      setIsConnected(false);
    }
  }, [updateTaskProgress, fetchTaskDetails, addToast]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      wsRef.current?.close();
    };
  }, [connect]);

  return { isConnected };
}
