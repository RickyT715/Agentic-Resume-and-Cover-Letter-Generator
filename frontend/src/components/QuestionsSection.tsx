import { useState } from 'react';
import { ChevronDown, ChevronRight, Plus, Trash2, Sparkles, Copy, Check, AlertCircle, Loader2 } from 'lucide-react';
import { ApplicationQuestion } from '../types/task';
import { useTaskStore } from '../store/taskStore';

const API_URL = '/api';

interface QuestionsSectionProps {
  taskId: string;
  questions: ApplicationQuestion[];
  jobDescription: string;
}

export function QuestionsSection({ taskId, questions, jobDescription }: QuestionsSectionProps) {
  const { updateTask, addToast } = useTaskStore();
  const [expanded, setExpanded] = useState(true);
  const [newQuestion, setNewQuestion] = useState('');
  const [newWordLimit, setNewWordLimit] = useState(150);
  const [adding, setAdding] = useState(false);
  const [generatingAll, setGeneratingAll] = useState(false);
  const [generatingIds, setGeneratingIds] = useState<Set<string>>(new Set());
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editQuestion, setEditQuestion] = useState('');
  const [editWordLimit, setEditWordLimit] = useState(150);

  const handleAddQuestion = async () => {
    if (!newQuestion.trim()) return;
    setAdding(true);
    try {
      const r = await fetch(`${API_URL}/tasks/${taskId}/questions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: newQuestion, word_limit: newWordLimit }),
      });
      if (r.ok) {
        const q: ApplicationQuestion = await r.json();
        updateTask(taskId, { questions: [...questions, q] });
        setNewQuestion('');
        setNewWordLimit(150);
      }
    } catch (e) {
      addToast('error', 'Failed to add question');
    } finally {
      setAdding(false);
    }
  };

  const handleDeleteQuestion = async (questionId: string) => {
    try {
      const r = await fetch(`${API_URL}/tasks/${taskId}/questions/${questionId}`, { method: 'DELETE' });
      if (r.ok) {
        updateTask(taskId, { questions: questions.filter((q) => q.id !== questionId) });
      }
    } catch (e) {
      addToast('error', 'Failed to delete question');
    }
  };

  const handleGenerate = async (questionId: string) => {
    setGeneratingIds((prev) => new Set(prev).add(questionId));
    // Optimistic: set status to running
    updateTask(taskId, {
      questions: questions.map((q) =>
        q.id === questionId ? { ...q, status: 'running' as const, error_message: undefined } : q
      ),
    });
    try {
      const r = await fetch(`${API_URL}/tasks/${taskId}/questions/${questionId}/generate`, { method: 'POST' });
      if (r.ok) {
        const updated: ApplicationQuestion = await r.json();
        updateTask(taskId, {
          questions: questions.map((q) => (q.id === questionId ? updated : q)),
        });
        if (updated.status === 'failed') {
          addToast('error', `Failed: ${updated.error_message}`);
        }
      } else {
        const data = await r.json();
        addToast('error', data.detail || 'Failed to generate answer');
        updateTask(taskId, {
          questions: questions.map((q) =>
            q.id === questionId ? { ...q, status: 'failed' as const, error_message: data.detail } : q
          ),
        });
      }
    } catch (e) {
      addToast('error', 'Failed to generate answer');
      updateTask(taskId, {
        questions: questions.map((q) =>
          q.id === questionId ? { ...q, status: 'failed' as const, error_message: 'Network error' } : q
        ),
      });
    } finally {
      setGeneratingIds((prev) => {
        const next = new Set(prev);
        next.delete(questionId);
        return next;
      });
    }
  };

  const handleGenerateAll = async () => {
    setGeneratingAll(true);
    try {
      const r = await fetch(`${API_URL}/tasks/${taskId}/questions/generate-all`, { method: 'POST' });
      if (r.ok) {
        const updatedQuestions: ApplicationQuestion[] = await r.json();
        updateTask(taskId, { questions: updatedQuestions });
        const failedCount = updatedQuestions.filter((q) => q.status === 'failed').length;
        if (failedCount > 0) {
          addToast('error', `${failedCount} question(s) failed to generate`);
        } else {
          addToast('success', 'All answers generated');
        }
      } else {
        const data = await r.json();
        addToast('error', data.detail || 'Failed to generate answers');
      }
    } catch (e) {
      addToast('error', 'Failed to generate answers');
    } finally {
      setGeneratingAll(false);
    }
  };

  const handleCopy = async (text: string, questionId: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedId(questionId);
      setTimeout(() => setCopiedId(null), 2000);
    } catch {
      addToast('error', 'Failed to copy');
    }
  };

  const handleStartEdit = (q: ApplicationQuestion) => {
    setEditingId(q.id);
    setEditQuestion(q.question);
    setEditWordLimit(q.word_limit);
  };

  const handleSaveEdit = async (questionId: string) => {
    try {
      const r = await fetch(`${API_URL}/tasks/${taskId}/questions/${questionId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: editQuestion, word_limit: editWordLimit }),
      });
      if (r.ok) {
        const updated: ApplicationQuestion = await r.json();
        updateTask(taskId, {
          questions: questions.map((q) => (q.id === questionId ? updated : q)),
        });
      }
    } catch (e) {
      addToast('error', 'Failed to update question');
    } finally {
      setEditingId(null);
    }
  };

  const unansweredCount = questions.filter((q) => q.status !== 'completed' || !q.answer).length;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-3 bg-gray-50 dark:bg-gray-750 border-b border-gray-200 dark:border-gray-700 flex items-center gap-2 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
      >
        {expanded ? <ChevronDown className="w-4 h-4 text-gray-500" /> : <ChevronRight className="w-4 h-4 text-gray-500" />}
        <Sparkles className="w-4 h-4 text-purple-500" />
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Application Questions</span>
        {questions.length > 0 && (
          <span className="ml-auto px-2 py-0.5 text-xs rounded-full bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400">
            {questions.length}
          </span>
        )}
      </button>

      {expanded && (
        <div className="p-4 space-y-4">
          {/* Add form */}
          <div className="space-y-2">
            <textarea
              value={newQuestion}
              onChange={(e) => setNewQuestion(e.target.value)}
              placeholder="Enter an application question (e.g., 'Why do you want to work here?')"
              className="w-full h-20 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg resize-none text-sm bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            />
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <label className="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">Word limit:</label>
                <input
                  type="number"
                  value={newWordLimit}
                  onChange={(e) => setNewWordLimit(Math.min(500, Math.max(50, Number(e.target.value))))}
                  min={50}
                  max={500}
                  className="w-20 px-2 py-1 border border-gray-300 dark:border-gray-600 rounded text-sm text-center bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                />
              </div>
              <button
                onClick={handleAddQuestion}
                disabled={!newQuestion.trim() || adding}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:bg-gray-300 dark:disabled:bg-gray-600 disabled:cursor-not-allowed transition-colors text-sm font-medium"
              >
                {adding ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />}
                Add
              </button>
            </div>
          </div>

          {/* Question list */}
          {questions.length > 0 && (
            <div className="space-y-3">
              {questions.map((q) => (
                <div
                  key={q.id}
                  className="border border-gray-200 dark:border-gray-600 rounded-lg overflow-hidden"
                >
                  <div className="px-3 py-2 bg-gray-50 dark:bg-gray-750 flex items-start gap-2">
                    <div className="flex-1 min-w-0">
                      {editingId === q.id ? (
                        <div className="space-y-2">
                          <textarea
                            value={editQuestion}
                            onChange={(e) => setEditQuestion(e.target.value)}
                            className="w-full h-16 px-2 py-1 border border-gray-300 dark:border-gray-600 rounded text-sm bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 resize-none"
                          />
                          <div className="flex items-center gap-2">
                            <label className="text-xs text-gray-500 dark:text-gray-400">Limit:</label>
                            <input
                              type="number"
                              value={editWordLimit}
                              onChange={(e) => setEditWordLimit(Math.min(500, Math.max(50, Number(e.target.value))))}
                              min={50}
                              max={500}
                              className="w-16 px-1 py-0.5 border border-gray-300 dark:border-gray-600 rounded text-xs text-center bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                            />
                            <button
                              onClick={() => handleSaveEdit(q.id)}
                              className="px-2 py-0.5 bg-blue-600 text-white rounded text-xs hover:bg-blue-700"
                            >
                              Save
                            </button>
                            <button
                              onClick={() => setEditingId(null)}
                              className="px-2 py-0.5 bg-gray-300 dark:bg-gray-600 text-gray-700 dark:text-gray-300 rounded text-xs hover:bg-gray-400 dark:hover:bg-gray-500"
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      ) : (
                        <p
                          className="text-sm text-gray-800 dark:text-gray-200 cursor-pointer hover:text-purple-600 dark:hover:text-purple-400"
                          onClick={() => handleStartEdit(q)}
                          title="Click to edit"
                        >
                          {q.question}
                        </p>
                      )}
                      {editingId !== q.id && (
                        <span className="text-xs text-gray-400 dark:text-gray-500">
                          {q.word_limit} words max
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-1 flex-shrink-0">
                      <button
                        onClick={() => handleGenerate(q.id)}
                        disabled={generatingIds.has(q.id) || generatingAll || !jobDescription.trim()}
                        className="p-1.5 text-purple-600 dark:text-purple-400 hover:bg-purple-50 dark:hover:bg-purple-900/20 rounded disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                        title={q.answer ? 'Regenerate answer' : 'Generate answer'}
                      >
                        {generatingIds.has(q.id) ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <Sparkles className="w-4 h-4" />
                        )}
                      </button>
                      <button
                        onClick={() => handleDeleteQuestion(q.id)}
                        disabled={generatingIds.has(q.id)}
                        className="p-1.5 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded disabled:opacity-40 transition-colors"
                        title="Delete question"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  {/* Answer display */}
                  {q.answer && (
                    <div className="px-3 py-2 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-600">
                      <div className="flex items-start gap-2">
                        <p className="flex-1 text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                          {q.answer}
                        </p>
                        <button
                          onClick={() => handleCopy(q.answer!, q.id)}
                          className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 flex-shrink-0"
                          title="Copy answer"
                        >
                          {copiedId === q.id ? (
                            <Check className="w-4 h-4 text-green-500" />
                          ) : (
                            <Copy className="w-4 h-4" />
                          )}
                        </button>
                      </div>
                      <span className="text-xs text-gray-400 dark:text-gray-500 mt-1 block">
                        {q.answer.split(/\s+/).length} words
                      </span>
                    </div>
                  )}

                  {/* Error display */}
                  {q.status === 'failed' && q.error_message && (
                    <div className="px-3 py-2 bg-red-50 dark:bg-red-900/20 border-t border-red-200 dark:border-red-800 flex items-center gap-2">
                      <AlertCircle className="w-3.5 h-3.5 text-red-500 flex-shrink-0" />
                      <span className="text-xs text-red-600 dark:text-red-400">{q.error_message}</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Generate All button */}
          {questions.length > 0 && unansweredCount > 0 && (
            <button
              onClick={handleGenerateAll}
              disabled={generatingAll || !jobDescription.trim()}
              className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:bg-gray-300 dark:disabled:bg-gray-600 disabled:cursor-not-allowed transition-colors text-sm font-medium"
            >
              {generatingAll ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Generating answers...
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  Generate All Answers ({unansweredCount})
                </>
              )}
            </button>
          )}

          {!jobDescription.trim() && questions.length > 0 && (
            <p className="text-xs text-amber-600 dark:text-amber-400 text-center">
              A job description is required to generate answers.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
