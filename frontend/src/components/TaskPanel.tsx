import { useState, useEffect, useCallback } from 'react';
import { Play, Download, AlertCircle, FileText, FileCheck, RefreshCw, Code, Eye, History, ClipboardList, Copy, Check } from 'lucide-react';
import { useTaskStore } from '../store/taskStore';
import { ProgressDisplay } from './ProgressDisplay';
import { QuestionsSection } from './QuestionsSection';
import { Template, JDHistoryEntry } from '../types/task';

const API_URL = '/api';

export function TaskPanel() {
  const { activeTaskId, tasks, updateTask, updateTaskJobDescription, addToast } = useTaskStore();
  const activeTask = tasks.find((t) => t.id === activeTaskId);
  const [jobDescription, setJobDescription] = useState('');
  const [generateCoverLetter, setGenerateCoverLetter] = useState(true);
  const [templateId, setTemplateId] = useState('classic');
  const [language, setLanguage] = useState('en');
  const [provider, setProvider] = useState<string>('');
  const [templates, setTemplates] = useState<Template[]>([]);
  const [jdHistory, setJdHistory] = useState<JDHistoryEntry[]>([]);
  const [showJdHistory, setShowJdHistory] = useState(false);
  const [isStarting, setIsStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [previewTab, setPreviewTab] = useState<'resume' | 'cover'>('resume');
  const [copiedAnswerId, setCopiedAnswerId] = useState<string | null>(null);
  const [copiedAll, setCopiedAll] = useState(false);

  // Load templates
  useEffect(() => {
    fetch(`${API_URL}/templates`)
      .then((r) => r.ok ? r.json() : [])
      .then(setTemplates)
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (activeTask) {
      setJobDescription(activeTask.job_description);
      setGenerateCoverLetter(activeTask.generate_cover_letter ?? true);
      setTemplateId(activeTask.template_id || 'classic');
      setLanguage(activeTask.language || 'en');
      setProvider(activeTask.provider || '');
      setError(null);
    }
  }, [activeTaskId, activeTask]);

  const loadJdHistory = async () => {
    try {
      const r = await fetch(`${API_URL}/jd-history`);
      if (r.ok) setJdHistory(await r.json());
    } catch (_) {}
  };

  const handleJobDescriptionChange = (value: string) => {
    setJobDescription(value);
    if (activeTask && activeTask.status === 'pending') {
      updateTaskJobDescription(activeTask.id, value);
    }
  };

  const handleCoverLetterToggle = async () => {
    if (!activeTask || activeTask.status !== 'pending') return;
    const newValue = !generateCoverLetter;
    setGenerateCoverLetter(newValue);
    try {
      const response = await fetch(`${API_URL}/tasks/${activeTask.id}/settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ generate_cover_letter: newValue, job_description: jobDescription }),
      });
      if (response.ok) updateTask(activeTask.id, await response.json());
    } catch (e) {
      console.error('Failed to update cover letter setting:', e);
    }
  };

  const handleTemplateChange = async (newTemplateId: string) => {
    setTemplateId(newTemplateId);
    if (!activeTask || activeTask.status !== 'pending') return;
    try {
      const response = await fetch(`${API_URL}/tasks/${activeTask.id}/settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ template_id: newTemplateId, job_description: jobDescription }),
      });
      if (response.ok) updateTask(activeTask.id, await response.json());
    } catch (e) {
      console.error('Failed to update template:', e);
    }
  };

  const handleLanguageChange = async (newLanguage: string) => {
    setLanguage(newLanguage);
    if (!activeTask || activeTask.status !== 'pending') return;
    try {
      const response = await fetch(`${API_URL}/tasks/${activeTask.id}/settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ language: newLanguage, job_description: jobDescription }),
      });
      if (response.ok) updateTask(activeTask.id, await response.json());
    } catch (e) {
      console.error('Failed to update language:', e);
    }
  };

  const handleProviderChange = async (newProvider: string) => {
    setProvider(newProvider);
    if (!activeTask || activeTask.status !== 'pending') return;
    try {
      const response = await fetch(`${API_URL}/tasks/${activeTask.id}/settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider: newProvider, job_description: jobDescription }),
      });
      if (response.ok) updateTask(activeTask.id, await response.json());
    } catch (e) {
      console.error('Failed to update provider:', e);
    }
  };

  const handleStartTask = async () => {
    if (!activeTask || !jobDescription.trim()) {
      setError('Please enter a job description');
      return;
    }
    setIsStarting(true);
    setError(null);
    try {
      const updateResponse = await fetch(`${API_URL}/tasks/${activeTask.id}/settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          job_description: jobDescription,
          generate_cover_letter: generateCoverLetter,
          template_id: templateId,
          provider: provider || undefined,
        }),
      });
      if (!updateResponse.ok) {
        const data = await updateResponse.json();
        throw new Error(data.detail || 'Failed to update task');
      }
      updateTask(activeTask.id, {
        job_description: jobDescription,
        generate_cover_letter: generateCoverLetter,
        status: 'running',
      });
      const startResponse = await fetch(`${API_URL}/tasks/${activeTask.id}/start`, { method: 'POST' });
      if (!startResponse.ok) {
        const data = await startResponse.json();
        throw new Error(data.detail || 'Failed to start task');
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'An error occurred');
      if (activeTask) updateTask(activeTask.id, { status: 'pending' });
    } finally {
      setIsStarting(false);
    }
  };

  const handleCopyAnswer = async (text: string, id: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedAnswerId(id);
      setTimeout(() => setCopiedAnswerId(null), 2000);
    } catch {
      addToast('error', 'Failed to copy');
    }
  };

  const handleCopyAll = async () => {
    const answeredQuestions = (activeTask?.questions || []).filter((q) => q.answer);
    const formatted = answeredQuestions
      .map((q) => `Q: ${q.question}\nA: ${q.answer}`)
      .join('\n\n');
    try {
      await navigator.clipboard.writeText(formatted);
      setCopiedAll(true);
      setTimeout(() => setCopiedAll(false), 2000);
    } catch {
      addToast('error', 'Failed to copy');
    }
  };

  // Ctrl+Enter to start
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter' && activeTask?.status === 'pending') {
        e.preventDefault();
        handleStartTask();
      }
    },
    [activeTask, jobDescription, generateCoverLetter, templateId, language, provider]
  );

  const handleRetry = async () => {
    if (!activeTask) return;
    try {
      const response = await fetch(`${API_URL}/tasks/${activeTask.id}/retry`, { method: 'POST' });
      if (!response.ok) {
        addToast('error', 'Failed to retry task');
        return;
      }
      // Re-fetch the task to get properly serialized data
      const taskRes = await fetch(`${API_URL}/tasks/${activeTask.id}`);
      if (taskRes.ok) {
        const task = await taskRes.json();
        updateTask(activeTask.id, task);
        addToast('info', 'Task reset for retry');
      }
    } catch (e) {
      console.error('Failed to retry task:', e);
      addToast('error', 'Failed to retry task');
    }
  };

  if (!activeTask) {
    return (
      <div className="flex-1 flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="text-center text-gray-500 dark:text-gray-400">
          <FileText className="w-16 h-16 mx-auto mb-4 opacity-30" />
          <p className="text-lg font-medium">No task selected</p>
          <p className="text-sm mt-1">Create a new task or select one from the sidebar</p>
        </div>
      </div>
    );
  }

  const isPending = activeTask.status === 'pending';
  const isCompleted = activeTask.status === 'completed';
  const isFailed = activeTask.status === 'failed';
  const isCancelled = activeTask.status === 'cancelled';
  const hasResume = !!activeTask.resume_pdf_path;
  const hasCoverLetter = activeTask.generate_cover_letter && !!activeTask.cover_letter_pdf_path;

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-gray-50 dark:bg-gray-900" onKeyDown={handleKeyDown}>
      {/* Header */}
      <div className="px-6 py-4 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-100">
              {activeTask.company_name && activeTask.position_name
                ? `${activeTask.company_name} - ${activeTask.position_name}`
                : activeTask.company_name || (activeTask.status === 'pending' ? 'New Task' : `Task ${activeTask.task_number}`)}
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
              Status:{' '}
              <span
                className={`font-medium ${
                  isCompleted ? 'text-green-600' :
                  isFailed ? 'text-red-600' :
                  activeTask.status === 'running' ? 'text-blue-600' :
                  isCancelled ? 'text-gray-500' :
                  'text-gray-600 dark:text-gray-400'
                }`}
              >
                {activeTask.status.charAt(0).toUpperCase() + activeTask.status.slice(1)}
              </span>
            </p>
          </div>
          {(isCompleted || isFailed || isCancelled) && (
            <button
              onClick={handleRetry}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
            >
              <RefreshCw className="w-4 h-4" />
              Retry Task
            </button>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* Job Description */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
          <div className="px-4 py-3 bg-gray-50 dark:bg-gray-750 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Job Description</label>
            {isPending && (
              <button
                onClick={() => { loadJdHistory(); setShowJdHistory(!showJdHistory); }}
                className="flex items-center gap-1 text-xs text-gray-500 hover:text-blue-600 dark:text-gray-400 dark:hover:text-blue-400"
              >
                <History className="w-3.5 h-3.5" />
                History
              </button>
            )}
          </div>

          {/* JD History Dropdown */}
          {showJdHistory && jdHistory.length > 0 && (
            <div className="border-b border-gray-200 dark:border-gray-700 max-h-40 overflow-y-auto">
              {jdHistory.map((jd, i) => (
                <button
                  key={i}
                  onClick={() => { handleJobDescriptionChange(jd.text); setShowJdHistory(false); }}
                  className="w-full text-left px-4 py-2 text-xs hover:bg-blue-50 dark:hover:bg-blue-900/20 border-b border-gray-100 dark:border-gray-700 last:border-0"
                >
                  <span className="text-gray-700 dark:text-gray-300 line-clamp-2">{jd.preview}</span>
                  <span className="text-gray-400 dark:text-gray-500 text-[10px]">{new Date(jd.saved_at).toLocaleDateString()}</span>
                </button>
              ))}
            </div>
          )}

          <div className="p-4">
            <textarea
              value={jobDescription}
              onChange={(e) => handleJobDescriptionChange(e.target.value)}
              disabled={!isPending}
              placeholder="Paste the job description here..."
              className="w-full h-56 px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-50 dark:disabled:bg-gray-700 disabled:text-gray-500 text-sm leading-relaxed bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
            />

            {error && (
              <div className="mt-3 flex items-center gap-2 text-red-600 text-sm">
                <AlertCircle className="w-4 h-4" />
                {error}
              </div>
            )}

            {isPending && (
              <div className="mt-4 space-y-4">
                {/* Template Selection */}
                {templates.length > 0 && (
                  <div className="flex items-center gap-3">
                    <label className="text-sm text-gray-600 dark:text-gray-400 whitespace-nowrap">Template:</label>
                    <select
                      value={templateId}
                      onChange={(e) => handleTemplateChange(e.target.value)}
                      className="px-3 py-1.5 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-300 focus:ring-2 focus:ring-blue-500"
                    >
                      {templates.map((t) => (
                        <option key={t.id} value={t.id}>{t.name} - {t.description}</option>
                      ))}
                    </select>
                  </div>
                )}

                {/* Language Selection */}
                <div className="flex items-center gap-3">
                  <label className="text-sm text-gray-600 dark:text-gray-400 whitespace-nowrap">Language:</label>
                  <div className="flex rounded-lg border border-gray-300 dark:border-gray-600 overflow-hidden">
                    <button
                      onClick={() => handleLanguageChange('en')}
                      className={`px-3 py-1.5 text-sm font-medium transition-colors ${
                        language === 'en'
                          ? 'bg-blue-600 text-white'
                          : 'bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800'
                      }`}
                    >
                      EN
                    </button>
                    <button
                      onClick={() => handleLanguageChange('zh')}
                      className={`px-3 py-1.5 text-sm font-medium transition-colors border-l border-gray-300 dark:border-gray-600 ${
                        language === 'zh'
                          ? 'bg-blue-600 text-white'
                          : 'bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800'
                      }`}
                    >
                      中文
                    </button>
                  </div>
                </div>

                {/* AI Provider Selection */}
                <div className="flex items-center gap-3">
                  <label className="text-sm text-gray-600 dark:text-gray-400 whitespace-nowrap">AI Provider:</label>
                  <select
                    value={provider}
                    onChange={(e) => handleProviderChange(e.target.value)}
                    className="px-3 py-1.5 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-300 focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">Default (from Settings)</option>
                    <option value="gemini">Google Gemini</option>
                    <option value="claude">Anthropic Claude</option>
                    <option value="openai_compat">OpenAI-Compatible Proxy</option>
                    <option value="claude_proxy">Claude Code Proxy</option>
                  </select>
                </div>

                {/* Cover Letter Toggle */}
                <div className="flex items-center gap-3">
                  <button
                    onClick={handleCoverLetterToggle}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                      generateCoverLetter ? 'bg-blue-600' : 'bg-gray-300 dark:bg-gray-600'
                    }`}
                    role="switch"
                    aria-checked={generateCoverLetter}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                        generateCoverLetter ? 'translate-x-6' : 'translate-x-1'
                      }`}
                    />
                  </button>
                  <div className="flex items-center gap-2">
                    <FileCheck className={`w-4 h-4 ${generateCoverLetter ? 'text-blue-600' : 'text-gray-400'}`} />
                    <span className={`text-sm font-medium ${generateCoverLetter ? 'text-gray-700 dark:text-gray-200' : 'text-gray-500'}`}>
                      Generate Cover Letter
                    </span>
                  </div>
                  <span className="text-xs text-gray-400">
                    {generateCoverLetter ? '(Resume + Cover Letter)' : '(Resume Only)'}
                  </span>
                </div>

                {/* Start Button */}
                <button
                  onClick={handleStartTask}
                  disabled={!jobDescription.trim() || isStarting}
                  className="flex items-center gap-2 px-5 py-2.5 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-300 dark:disabled:bg-gray-600 disabled:cursor-not-allowed transition-colors font-medium"
                >
                  {isStarting ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      Starting...
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4" />
                      Start Task
                      <span className="text-xs opacity-75 ml-1">(Ctrl+Enter)</span>
                    </>
                  )}
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Application Questions */}
        <QuestionsSection
          taskId={activeTask.id}
          questions={activeTask.questions || []}
          jobDescription={jobDescription}
        />

        {/* Generated Answers Panel */}
        {(activeTask.questions || []).some((q) => q.answer) && (
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
            <div className="px-4 py-3 bg-gray-50 dark:bg-gray-750 border-b border-gray-200 dark:border-gray-700 flex items-center gap-2">
              <ClipboardList className="w-4 h-4 text-purple-500" />
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Generated Answers</span>
              <span className="px-2 py-0.5 text-xs rounded-full bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400">
                {(activeTask.questions || []).filter((q) => q.answer).length}
              </span>
              <button
                onClick={handleCopyAll}
                className="ml-auto flex items-center gap-1.5 px-3 py-1 text-xs font-medium text-purple-600 dark:text-purple-400 hover:bg-purple-50 dark:hover:bg-purple-900/20 rounded transition-colors"
              >
                {copiedAll ? <Check className="w-3.5 h-3.5 text-green-500" /> : <Copy className="w-3.5 h-3.5" />}
                {copiedAll ? 'Copied!' : 'Copy All'}
              </button>
            </div>
            <div className="p-4 space-y-4">
              {(activeTask.questions || [])
                .filter((q) => q.answer)
                .map((q) => (
                  <div key={q.id} className="border border-gray-200 dark:border-gray-600 rounded-lg overflow-hidden">
                    <div className="px-3 py-2 bg-gray-50 dark:bg-gray-750">
                      <p className="text-sm font-medium text-gray-600 dark:text-gray-400">{q.question}</p>
                    </div>
                    <div className="px-3 py-2 bg-white dark:bg-gray-800">
                      <div className="flex items-start gap-2">
                        <p className="flex-1 text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">{q.answer}</p>
                        <button
                          onClick={() => handleCopyAnswer(q.answer!, q.id)}
                          className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 flex-shrink-0"
                          title="Copy answer"
                        >
                          {copiedAnswerId === q.id ? (
                            <Check className="w-4 h-4 text-green-500" />
                          ) : (
                            <Copy className="w-4 h-4" />
                          )}
                        </button>
                      </div>
                      <span className="text-xs text-gray-400 dark:text-gray-500 mt-1 block">
                        {q.answer!.split(/\s+/).length} words
                      </span>
                    </div>
                  </div>
                ))}
            </div>
          </div>
        )}

        {/* Progress */}
        {activeTask.status !== 'pending' && <ProgressDisplay task={activeTask} />}

        {/* Error / partial result */}
        {(isFailed || isCancelled) && activeTask.error_message && (
          <div className={`${isCancelled ? 'bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700' : 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800'} border rounded-xl p-4`}>
            <div className="flex items-start gap-3">
              <AlertCircle className={`w-5 h-5 flex-shrink-0 mt-0.5 ${isCancelled ? 'text-gray-500' : 'text-red-500'}`} />
              <div>
                <h3 className={`font-medium ${isCancelled ? 'text-gray-700 dark:text-gray-300' : 'text-red-800 dark:text-red-300'}`}>
                  {isCancelled ? 'Task Cancelled' : 'Task Failed'}
                </h3>
                <p className={`text-sm mt-1 ${isCancelled ? 'text-gray-600 dark:text-gray-400' : 'text-red-600 dark:text-red-400'}`}>
                  {activeTask.error_message}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Partial result notice for failed tasks with resume */}
        {isFailed && hasResume && (
          <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-xl p-4">
            <p className="text-sm text-yellow-800 dark:text-yellow-300 font-medium">
              Resume was generated before the failure and is available for download.
            </p>
          </div>
        )}

        {/* Downloads */}
        {(isCompleted || (isFailed && hasResume)) && (
          <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-xl p-5">
            <h3 className="font-semibold text-green-800 dark:text-green-300 mb-4 flex items-center gap-2">
              <CheckCircleIcon />
              Files Ready for Download
            </h3>
            <div className="flex flex-wrap gap-3">
              {hasResume && (
                <a
                  href={`${API_URL}/tasks/${activeTask.id}/resume`}
                  download
                  className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-gray-800 border border-green-300 dark:border-green-700 rounded-lg text-green-700 dark:text-green-400 hover:bg-green-50 dark:hover:bg-green-900/20 transition-colors font-medium shadow-sm text-sm"
                >
                  <Download className="w-4 h-4" />
                  Resume (PDF)
                </a>
              )}
              {hasCoverLetter && (
                <a
                  href={`${API_URL}/tasks/${activeTask.id}/cover-letter`}
                  download
                  className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-gray-800 border border-green-300 dark:border-green-700 rounded-lg text-green-700 dark:text-green-400 hover:bg-green-50 dark:hover:bg-green-900/20 transition-colors font-medium shadow-sm text-sm"
                >
                  <Download className="w-4 h-4" />
                  Cover Letter (PDF)
                </a>
              )}
              {activeTask.latex_source && (
                <a
                  href={`${API_URL}/tasks/${activeTask.id}/latex`}
                  download
                  className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors font-medium shadow-sm text-sm"
                >
                  <Code className="w-4 h-4" />
                  LaTeX Source (.tex)
                </a>
              )}
            </div>
          </div>
        )}

        {/* PDF Preview */}
        {(isCompleted || (isFailed && hasResume)) && (
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
            <div className="px-4 py-3 bg-gray-50 dark:bg-gray-750 border-b border-gray-200 dark:border-gray-700 flex items-center gap-2">
              <Eye className="w-4 h-4 text-gray-500" />
              <span className="font-medium text-gray-700 dark:text-gray-300 text-sm">PDF Preview</span>
              {hasCoverLetter && (
                <div className="flex ml-auto gap-1">
                  <button
                    onClick={() => setPreviewTab('resume')}
                    className={`px-3 py-1 text-xs rounded ${
                      previewTab === 'resume'
                        ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400'
                        : 'text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700'
                    }`}
                  >
                    Resume
                  </button>
                  <button
                    onClick={() => setPreviewTab('cover')}
                    className={`px-3 py-1 text-xs rounded ${
                      previewTab === 'cover'
                        ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400'
                        : 'text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700'
                    }`}
                  >
                    Cover Letter
                  </button>
                </div>
              )}
            </div>
            <div className="p-4">
              <iframe
                src={
                  previewTab === 'cover' && hasCoverLetter
                    ? `${API_URL}/tasks/${activeTask.id}/cover-letter?inline=true`
                    : `${API_URL}/tasks/${activeTask.id}/resume?inline=true`
                }
                className="w-full h-[600px] rounded border border-gray-200 dark:border-gray-600 bg-white"
                title="PDF Preview"
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function CheckCircleIcon() {
  return (
    <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  );
}
