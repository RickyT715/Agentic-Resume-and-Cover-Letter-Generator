import { useState } from 'react';
import { Play, AlertCircle, FileCheck, History, Globe, Loader2, Zap } from 'lucide-react';
import { Task, JDHistoryEntry } from '../../types/task';
import {
  useTemplatesQuery,
  useJdHistoryQuery,
  useScrapeCompanyMutation,
} from '../../hooks/useTaskQuery';
import { useTaskStore } from '../../store/taskStore';

const API_URL = '/api';

interface TaskCreationFormProps {
  activeTask: Task;
  jobDescription: string;
  onJobDescriptionChange: (value: string) => void;
  onStartTask: () => void;
  isStarting: boolean;
  error: string | null;
}

export function TaskCreationForm({
  activeTask,
  jobDescription,
  onJobDescriptionChange,
  onStartTask,
  isStarting,
  error,
}: TaskCreationFormProps) {
  const { updateTask, addToast } = useTaskStore();
  const [generateCoverLetter, setGenerateCoverLetter] = useState(
    activeTask.generate_cover_letter ?? true,
  );
  const [templateId, setTemplateId] = useState(activeTask.template_id || 'classic');
  const [language, setLanguage] = useState(activeTask.language || 'en');
  const [experienceLevel, setExperienceLevel] = useState(activeTask.experience_level || 'auto');
  const [provider, setProvider] = useState<string>(activeTask.provider || '');
  const [showJdHistory, setShowJdHistory] = useState(false);
  const [pipelineVersion, setPipelineVersion] = useState<'v2' | 'v3'>('v3');
  const [companyUrl, setCompanyUrl] = useState('');
  const [scrapeStatus, setScrapeStatus] = useState<string | null>(null);

  const { data: templates = [] } = useTemplatesQuery();
  const { data: jdHistory = [], refetch: refetchHistory } = useJdHistoryQuery(showJdHistory);
  const scrapeMutation = useScrapeCompanyMutation();

  const isPending = activeTask.status === 'pending';

  const updateTaskSetting = async (settings: Record<string, unknown>) => {
    if (!isPending) return;
    try {
      const response = await fetch(`${API_URL}/tasks/${activeTask.id}/settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...settings, job_description: jobDescription }),
      });
      if (response.ok) updateTask(activeTask.id, await response.json());
    } catch (e) {
      console.error('Failed to update task setting:', e);
    }
  };

  const handleCoverLetterToggle = () => {
    const newValue = !generateCoverLetter;
    setGenerateCoverLetter(newValue);
    updateTaskSetting({ generate_cover_letter: newValue });
  };

  const handleTemplateChange = (newTemplateId: string) => {
    setTemplateId(newTemplateId);
    updateTaskSetting({ template_id: newTemplateId });
  };

  const handleLanguageChange = (newLanguage: string) => {
    setLanguage(newLanguage);
    updateTaskSetting({ language: newLanguage });
  };

  const handleExperienceLevelChange = (newLevel: string) => {
    setExperienceLevel(newLevel);
    updateTaskSetting({ experience_level: newLevel });
    fetch(`/api/settings`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ default_experience_level: newLevel }),
    }).catch(() => {});
  };

  const handleProviderChange = (newProvider: string) => {
    setProvider(newProvider);
    updateTaskSetting({ provider: newProvider });
  };

  const handleScrapeCompany = () => {
    if (!companyUrl.trim()) return;
    setScrapeStatus(null);
    try {
      const hostname = new URL(companyUrl).hostname.replace('www.', '');
      const companyName = hostname.split('.')[0];
      scrapeMutation.mutate(
        { url: companyUrl, company_name: companyName },
        {
          onSuccess: (result) => {
            setScrapeStatus(
              `Indexed ${result.chunks_indexed} chunks from ${result.pages_scraped} pages`,
            );
            addToast('success', `Company research indexed for ${companyName}`);
          },
          onError: (e) => {
            setScrapeStatus(e.message);
            addToast('error', e.message);
          },
        },
      );
    } catch {
      setScrapeStatus('Invalid URL');
      addToast('error', 'Invalid URL');
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
      <div className="px-4 py-3 bg-gray-50 dark:bg-gray-750 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
          Job Description
        </label>
        {isPending && (
          <button
            onClick={() => {
              refetchHistory();
              setShowJdHistory(!showJdHistory);
            }}
            className="flex items-center gap-1 text-xs text-gray-500 hover:text-blue-600 dark:text-gray-400 dark:hover:text-blue-400"
          >
            <History className="w-3.5 h-3.5" />
            History
          </button>
        )}
      </div>

      {showJdHistory && jdHistory.length > 0 && (
        <div className="border-b border-gray-200 dark:border-gray-700 max-h-40 overflow-y-auto">
          {jdHistory.map((jd: JDHistoryEntry, i: number) => (
            <button
              key={i}
              onClick={() => {
                onJobDescriptionChange(jd.text);
                setShowJdHistory(false);
              }}
              className="w-full text-left px-4 py-2 text-xs hover:bg-blue-50 dark:hover:bg-blue-900/20 border-b border-gray-100 dark:border-gray-700 last:border-0"
            >
              <span className="text-gray-700 dark:text-gray-300 line-clamp-2">{jd.preview}</span>
              <span className="text-gray-400 dark:text-gray-500 text-[10px]">
                {new Date(jd.saved_at).toLocaleDateString()}
              </span>
            </button>
          ))}
        </div>
      )}

      <div className="p-4">
        <textarea
          value={jobDescription}
          onChange={(e) => onJobDescriptionChange(e.target.value)}
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
                <label className="text-sm text-gray-600 dark:text-gray-400 whitespace-nowrap">
                  Template:
                </label>
                <select
                  value={templateId}
                  onChange={(e) => handleTemplateChange(e.target.value)}
                  className="px-3 py-1.5 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-300 focus:ring-2 focus:ring-blue-500"
                >
                  {templates.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name} - {t.description}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Language Selection */}
            <div className="flex items-center gap-3">
              <label className="text-sm text-gray-600 dark:text-gray-400 whitespace-nowrap">
                Language:
              </label>
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

            {/* Experience Level Selection */}
            <div className="flex items-center gap-3">
              <label className="text-sm text-gray-600 dark:text-gray-400 whitespace-nowrap">
                Experience:
              </label>
              <div className="flex rounded-lg border border-gray-300 dark:border-gray-600 overflow-hidden">
                {(
                  [
                    { value: 'auto', label: 'Auto' },
                    { value: 'new_grad', label: 'New Grad' },
                    { value: 'experienced', label: 'Experienced' },
                  ] as const
                ).map((opt, i) => (
                  <button
                    key={opt.value}
                    onClick={() => handleExperienceLevelChange(opt.value)}
                    className={`px-3 py-1.5 text-sm font-medium transition-colors ${
                      i > 0 ? 'border-l border-gray-300 dark:border-gray-600' : ''
                    } ${
                      experienceLevel === opt.value
                        ? 'bg-blue-600 text-white'
                        : 'bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800'
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>

            {/* AI Provider Selection */}
            <div className="flex items-center gap-3">
              <label className="text-sm text-gray-600 dark:text-gray-400 whitespace-nowrap">
                AI Provider:
              </label>
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

            {/* Company URL (RAG Research) */}
            <div className="flex items-center gap-3">
              <label className="text-sm text-gray-600 dark:text-gray-400 whitespace-nowrap">
                <Globe className="w-3.5 h-3.5 inline mr-1" />
                Company URL:
              </label>
              <div className="flex-1 flex gap-2">
                <input
                  type="url"
                  value={companyUrl}
                  onChange={(e) => setCompanyUrl(e.target.value)}
                  placeholder="https://company.com (optional)"
                  className="flex-1 px-3 py-1.5 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-300 focus:ring-2 focus:ring-blue-500 placeholder-gray-400"
                />
                <button
                  onClick={handleScrapeCompany}
                  disabled={!companyUrl.trim() || scrapeMutation.isPending}
                  className="px-3 py-1.5 text-sm font-medium bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:bg-gray-300 dark:disabled:bg-gray-600 disabled:cursor-not-allowed transition-colors flex items-center gap-1"
                >
                  {scrapeMutation.isPending ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Globe className="w-3.5 h-3.5" />
                  )}
                  {scrapeMutation.isPending ? 'Scraping...' : 'Research'}
                </button>
              </div>
              {scrapeStatus && (
                <span className="text-xs text-gray-500 dark:text-gray-400">{scrapeStatus}</span>
              )}
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
                <FileCheck
                  className={`w-4 h-4 ${generateCoverLetter ? 'text-blue-600' : 'text-gray-400'}`}
                />
                <span
                  className={`text-sm font-medium ${generateCoverLetter ? 'text-gray-700 dark:text-gray-200' : 'text-gray-500'}`}
                >
                  Generate Cover Letter
                </span>
              </div>
              <span className="text-xs text-gray-400">
                {generateCoverLetter ? '(Resume + Cover Letter)' : '(Resume Only)'}
              </span>
            </div>

            {/* Pipeline Version */}
            <div className="flex items-center gap-3">
              <label className="text-sm text-gray-600 dark:text-gray-400 whitespace-nowrap">
                Pipeline:
              </label>
              <div className="flex rounded-lg border border-gray-300 dark:border-gray-600 overflow-hidden">
                <button
                  onClick={() => setPipelineVersion('v3')}
                  className={`px-3 py-1.5 text-sm font-medium transition-colors flex items-center gap-1 ${
                    pipelineVersion === 'v3'
                      ? 'bg-purple-600 text-white'
                      : 'bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800'
                  }`}
                >
                  <Zap className="w-3 h-3" />
                  v3 Multi-Agent
                </button>
                <button
                  onClick={() => setPipelineVersion('v2')}
                  className={`px-3 py-1.5 text-sm font-medium transition-colors border-l border-gray-300 dark:border-gray-600 ${
                    pipelineVersion === 'v2'
                      ? 'bg-blue-600 text-white'
                      : 'bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800'
                  }`}
                >
                  v2 Classic
                </button>
              </div>
              {pipelineVersion === 'v3' && (
                <span className="text-xs text-purple-600 dark:text-purple-400">
                  JD Analysis + Relevance Match + Quality Gate
                </span>
              )}
            </div>

            {/* Start Button */}
            <button
              onClick={onStartTask}
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
  );
}
