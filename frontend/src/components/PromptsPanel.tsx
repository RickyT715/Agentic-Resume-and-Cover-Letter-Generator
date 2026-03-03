import { useState, useEffect, useCallback } from 'react';
import { FileText, Save, RefreshCw, X, AlertTriangle } from 'lucide-react';
import { useTaskStore } from '../store/taskStore';

type PromptKey =
  | 'resume_prompt'
  | 'cover_letter_prompt'
  | 'user_information'
  | 'resume_format'
  | 'application_question_prompt'
  | 'resume_prompt_zh'
  | 'cover_letter_prompt_zh'
  | 'user_information_zh'
  | 'resume_format_zh'
  | 'application_question_prompt_zh';

const PROMPT_LABELS: Record<PromptKey, { title: string; description: string }> = {
  resume_prompt: {
    title: 'Resume Prompt',
    description:
      'Main prompt for generating resumes. Uses {{user_information}} and {{latex_template}} placeholders.',
  },
  cover_letter_prompt: {
    title: 'Cover Letter Prompt',
    description:
      'Prompt for generating cover letters. Uses {{RESUME_CONTENT}} and {{JOB_DESCRIPTION}} placeholders.',
  },
  user_information: {
    title: 'User Information',
    description:
      'Your personal information (education, experience, projects, skills). Replaces {{user_information}} in resume prompt.',
  },
  resume_format: {
    title: 'Resume Format (LaTeX)',
    description:
      'LaTeX template for resume formatting. Replaces {{latex_template}} in resume prompt.',
  },
  application_question_prompt: {
    title: 'Application Q&A Prompt',
    description:
      'Prompt for answering application questions. Uses {{USER_INFORMATION}}, {{JOB_DESCRIPTION}}, {{QUESTION}}, {{WORD_LIMIT}}.',
  },
  resume_prompt_zh: {
    title: 'Resume Prompt',
    description: '简历生成主提示词。使用 {{user_information}} 和 {{latex_template}} 占位符。',
  },
  cover_letter_prompt_zh: {
    title: 'Cover Letter Prompt',
    description: '求职信生成提示词。使用 {{RESUME_CONTENT}} 和 {{JOB_DESCRIPTION}} 占位符。',
  },
  user_information_zh: {
    title: 'User Information',
    description:
      '您的个人信息（教育、经历、项目、技能）。替换简历提示词中的 {{user_information}}。',
  },
  resume_format_zh: {
    title: 'Resume Format (LaTeX)',
    description: '中文简历 LaTeX 模板。替换简历提示词中的 {{latex_template}}。',
  },
  application_question_prompt_zh: {
    title: 'Application Q&A Prompt',
    description:
      '求职申请问题回答提示词。使用 {{USER_INFORMATION}}、{{JOB_DESCRIPTION}}、{{QUESTION}}、{{WORD_LIMIT}}。',
  },
};

const EN_TABS: PromptKey[] = [
  'user_information',
  'resume_format',
  'resume_prompt',
  'cover_letter_prompt',
  'application_question_prompt',
];
const ZH_TABS: PromptKey[] = [
  'user_information_zh',
  'resume_format_zh',
  'resume_prompt_zh',
  'cover_letter_prompt_zh',
  'application_question_prompt_zh',
];

interface PromptsPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function PromptsPanel({ isOpen, onClose }: PromptsPanelProps) {
  const [prompts, setPrompts] = useState<Record<string, string> | null>(null);
  const [promptLang, setPromptLang] = useState<'en' | 'zh'>('en');
  const [activeTab, setActiveTab] = useState<PromptKey>('user_information');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [hasChanges, setHasChanges] = useState(false);
  const addToast = useTaskStore((state) => state.addToast);

  const tabs = promptLang === 'zh' ? ZH_TABS : EN_TABS;

  useEffect(() => {
    if (isOpen) {
      loadPrompts();
    }
  }, [isOpen]);

  // When switching language, reset active tab to first tab of that language
  const handleLangSwitch = (lang: 'en' | 'zh') => {
    setPromptLang(lang);
    setActiveTab(lang === 'zh' ? ZH_TABS[0] : EN_TABS[0]);
    setWarnings([]);
  };

  const loadPrompts = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/prompts');
      if (response.ok) {
        const data = await response.json();
        setPrompts(data);
        setHasChanges(false);
        setWarnings([]);
      }
    } catch (error) {
      console.error('Failed to load prompts:', error);
      addToast('error', 'Failed to load prompts');
    } finally {
      setLoading(false);
    }
  };

  const savePrompt = useCallback(
    async (key: PromptKey) => {
      if (!prompts) return;

      setSaving(true);
      setWarnings([]);

      try {
        const response = await fetch(`/api/prompts/${key}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ content: prompts[key] }),
        });

        if (response.ok) {
          const result = await response.json();
          if (result.warnings && result.warnings.length > 0) {
            setWarnings(result.warnings);
            addToast('info', `${PROMPT_LABELS[key].title} saved with warnings`);
          } else {
            addToast('success', `${PROMPT_LABELS[key].title} saved successfully!`);
          }
          setHasChanges(false);
        } else {
          throw new Error('Failed to save prompt');
        }
      } catch (error) {
        console.error('Failed to save prompt:', error);
        addToast('error', 'Failed to save prompt');
      } finally {
        setSaving(false);
      }
    },
    [prompts, addToast],
  );

  const updatePrompt = (key: PromptKey, value: string) => {
    setPrompts((prev) => (prev ? { ...prev, [key]: value } : null));
    setHasChanges(true);
    setWarnings([]);
  };

  const reloadPrompts = async () => {
    if (hasChanges && !confirm('You have unsaved changes. Reload anyway?')) return;

    setLoading(true);
    try {
      await fetch('/api/prompts/reload', { method: 'POST' });
      await loadPrompts();
      addToast('success', 'Prompts reloaded from files');
    } catch (error) {
      console.error('Failed to reload prompts:', error);
      addToast('error', 'Failed to reload prompts');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    if (hasChanges && !confirm('You have unsaved changes. Close anyway?')) return;
    onClose();
  };

  // Ctrl+S to save
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        if (hasChanges && !saving) {
          savePrompt(activeTab);
        }
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [isOpen, hasChanges, saving, activeTab, savePrompt]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-5xl max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-750">
          <div className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-gray-600 dark:text-gray-400" />
            <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100">Edit Prompts</h2>
          </div>
          <div className="flex items-center gap-3">
            {/* Language toggle */}
            <div className="flex rounded-lg border border-gray-300 dark:border-gray-600 overflow-hidden">
              <button
                onClick={() => handleLangSwitch('en')}
                className={`px-3 py-1 text-sm font-medium transition-colors ${
                  promptLang === 'en'
                    ? 'bg-blue-600 text-white'
                    : 'bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800'
                }`}
              >
                EN
              </button>
              <button
                onClick={() => handleLangSwitch('zh')}
                className={`px-3 py-1 text-sm font-medium transition-colors border-l border-gray-300 dark:border-gray-600 ${
                  promptLang === 'zh'
                    ? 'bg-blue-600 text-white'
                    : 'bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800'
                }`}
              >
                中文
              </button>
            </div>
            <button
              onClick={handleClose}
              className="p-1 hover:bg-gray-200 dark:hover:bg-gray-600 rounded text-gray-500 dark:text-gray-400"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-750 overflow-x-auto">
          {tabs.map((key) => (
            <button
              key={key}
              onClick={() => {
                setActiveTab(key);
                setWarnings([]);
              }}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                activeTab === key
                  ? 'border-blue-500 text-blue-600 dark:text-blue-400 bg-white dark:bg-gray-800'
                  : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
              }`}
            >
              {PROMPT_LABELS[key].title}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="p-4 h-[calc(90vh-200px)] flex flex-col">
          {loading ? (
            <div className="flex items-center justify-center py-8 flex-1">
              <RefreshCw className="w-6 h-6 animate-spin text-blue-500" />
            </div>
          ) : prompts ? (
            <>
              {/* Warnings */}
              {warnings.length > 0 && (
                <div className="p-3 rounded-lg mb-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800">
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="w-4 h-4 text-yellow-600 dark:text-yellow-400 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-sm font-medium text-yellow-800 dark:text-yellow-300">
                        Placeholder Warnings
                      </p>
                      <ul className="text-xs text-yellow-700 dark:text-yellow-400 mt-1 space-y-0.5">
                        {warnings.map((w, i) => (
                          <li key={i}>{w}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              )}

              {/* Description */}
              <div className="mb-3 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg text-sm text-blue-800 dark:text-blue-300 border border-blue-200 dark:border-blue-800">
                <strong>{PROMPT_LABELS[activeTab].title}:</strong>{' '}
                {PROMPT_LABELS[activeTab].description}
              </div>

              {/* Editor */}
              <div className="flex-1 relative">
                <textarea
                  value={prompts[activeTab] || ''}
                  onChange={(e) => updatePrompt(activeTab, e.target.value)}
                  className="w-full h-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 font-mono text-sm resize-none bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                  placeholder={`Enter ${PROMPT_LABELS[activeTab].title.toLowerCase()}...`}
                />
              </div>

              {/* Character count */}
              <div className="mt-2 text-xs text-gray-500 dark:text-gray-400 text-right">
                {prompts[activeTab]?.length || 0} characters
              </div>
            </>
          ) : (
            <div className="text-center py-8 text-gray-500 dark:text-gray-400 flex-1">
              Failed to load prompts
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-750">
          <button
            onClick={reloadPrompts}
            className="px-4 py-2 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg flex items-center gap-2"
          >
            <RefreshCw className="w-4 h-4" />
            Reload from Files
          </button>
          <div className="flex items-center gap-4">
            {hasChanges && (
              <span className="text-sm text-orange-600 dark:text-orange-400">Unsaved changes</span>
            )}
            <div className="flex gap-2">
              <button
                onClick={handleClose}
                className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300"
              >
                Close
              </button>
              <button
                onClick={() => savePrompt(activeTab)}
                disabled={saving || !hasChanges}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
              >
                <Save className="w-4 h-4" />
                {saving ? 'Saving...' : `Save`}
                <span className="text-xs opacity-75">(Ctrl+S)</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
