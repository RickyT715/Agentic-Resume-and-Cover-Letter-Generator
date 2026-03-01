import { useState, useEffect } from 'react';
import { Settings, Save, RefreshCw, X, ChevronDown, ChevronUp } from 'lucide-react';
import { useTaskStore } from '../store/taskStore';
import { Template } from '../types/task';

interface AppSettings {
  default_provider: string;
  // Gemini
  gemini_api_key: string;
  gemini_model: string;
  gemini_temperature: number | null;
  gemini_top_k: number | null;
  gemini_top_p: number | null;
  gemini_max_output_tokens: number | null;
  gemini_thinking_level: string;
  gemini_enable_search: boolean;
  // Claude
  claude_api_key: string;
  claude_model: string;
  claude_temperature: number | null;
  claude_max_output_tokens: number | null;
  claude_extended_thinking: boolean;
  claude_thinking_budget: number;
  // OpenAI-Compatible
  openai_compat_base_url: string;
  openai_compat_api_key: string;
  openai_compat_model: string;
  openai_compat_temperature: number | null;
  openai_compat_max_output_tokens: number | null;
  // Claude Code Proxy
  claude_proxy_base_url: string;
  claude_proxy_api_key: string;
  claude_proxy_model: string;
  claude_proxy_temperature: number | null;
  claude_proxy_max_output_tokens: number | null;
  // DeepSeek
  deepseek_api_key: string;
  deepseek_model: string;
  deepseek_temperature: number | null;
  deepseek_max_output_tokens: number | null;
  // Qwen (Alibaba)
  qwen_api_key: string;
  qwen_model: string;
  qwen_temperature: number | null;
  qwen_max_output_tokens: number | null;
  // General
  enforce_resume_one_page: boolean;
  enforce_cover_letter_one_page: boolean;
  max_page_retry_attempts: number;
  generate_cover_letter: boolean;
  max_latex_retries: number;
  default_template_id: string;
  // Per-Agent Providers
  agent_providers: Record<string, string>;
}

interface SettingsPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

export function SettingsPanel({ isOpen, onClose }: SettingsPanelProps) {
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [templates, setTemplates] = useState<Template[]>([]);
  const addToast = useTaskStore((state) => state.addToast);
  const [expandedSections, setExpandedSections] = useState({
    provider: true,
    agent_providers: false,
    gemini: true,
    claude: false,
    openai_compat: false,
    claude_proxy: false,
    deepseek: false,
    qwen: false,
    generation: true,
    validation: true,
  });

  useEffect(() => {
    if (isOpen) {
      loadSettings();
      fetch('/api/templates')
        .then((r) => r.ok ? r.json() : [])
        .then(setTemplates)
        .catch(() => {});
    }
  }, [isOpen]);

  const loadSettings = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/settings');
      if (response.ok) {
        const data = await response.json();
        setSettings(data);
      }
    } catch (error) {
      console.error('Failed to load settings:', error);
      addToast('error', 'Failed to load settings');
    } finally {
      setLoading(false);
    }
  };

  const saveSettings = async () => {
    if (!settings) return;

    setSaving(true);

    try {
      const response = await fetch('/api/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
      });

      if (response.ok) {
        addToast('success', 'Settings saved successfully!');
      } else {
        throw new Error('Failed to save settings');
      }
    } catch (error) {
      console.error('Failed to save settings:', error);
      addToast('error', 'Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const resetSettings = async () => {
    if (!confirm('Are you sure you want to reset all settings to defaults?')) return;

    setLoading(true);
    try {
      const response = await fetch('/api/settings/reset', { method: 'POST' });
      if (response.ok) {
        const data = await response.json();
        setSettings(data);
        addToast('success', 'Settings reset to defaults');
      }
    } catch (error) {
      console.error('Failed to reset settings:', error);
      addToast('error', 'Failed to reset settings');
    } finally {
      setLoading(false);
    }
  };

  const toggleSection = (section: keyof typeof expandedSections) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  const updateSetting = <K extends keyof AppSettings>(key: K, value: AppSettings[K]) => {
    setSettings(prev => prev ? { ...prev, [key]: value } : null);
  };

  const updateAgentProvider = (agent: string, provider: string) => {
    setSettings(prev => {
      if (!prev) return null;
      const current = prev.agent_providers || {};
      return { ...prev, agent_providers: { ...current, [agent]: provider } };
    });
  };

  const AGENT_LABELS: Record<string, string> = {
    jd_analyzer: 'JD Analyzer',
    relevance_matcher: 'Relevance Matcher',
    resume_writer: 'Resume Writer',
    cover_letter_writer: 'Cover Letter Writer',
    company_researcher: 'Company Researcher',
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-750">
          <div className="flex items-center gap-2">
            <Settings className="w-5 h-5 text-gray-600 dark:text-gray-400" />
            <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100">Application Settings</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-200 dark:hover:bg-gray-600 rounded text-gray-500 dark:text-gray-400"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 overflow-y-auto max-h-[calc(90vh-120px)]">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <RefreshCw className="w-6 h-6 animate-spin text-blue-500" />
            </div>
          ) : settings ? (
            <div className="space-y-4">
              {/* Default Provider Section */}
              <div className="border border-gray-200 dark:border-gray-700 rounded-lg">
                <button
                  onClick={() => toggleSection('provider')}
                  className="w-full flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-750 hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-800 dark:text-gray-200 rounded-t-lg"
                >
                  <span className="font-medium">Default AI Provider</span>
                  {expandedSections.provider ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </button>
                {expandedSections.provider && (
                  <div className="p-4">
                    <select
                      value={settings.default_provider || 'gemini'}
                      onChange={(e) => updateSetting('default_provider', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                    >
                      <option value="gemini">Google Gemini</option>
                      <option value="claude">Anthropic Claude</option>
                      <option value="openai_compat">OpenAI-Compatible Proxy</option>
                      <option value="claude_proxy">Claude Code Proxy</option>
                      <option value="deepseek">DeepSeek</option>
                      <option value="qwen">Qwen (Alibaba)</option>
                    </select>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      Provider used for new tasks by default. Individual tasks can override this.
                    </p>
                  </div>
                )}
              </div>

              {/* Per-Agent Provider Overrides Section */}
              <div className="border border-gray-200 dark:border-gray-700 rounded-lg">
                <button
                  onClick={() => toggleSection('agent_providers')}
                  className="w-full flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-750 hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-800 dark:text-gray-200 rounded-t-lg"
                >
                  <span className="font-medium">Per-Agent Provider Overrides</span>
                  {expandedSections.agent_providers ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </button>
                {expandedSections.agent_providers && (
                  <div className="p-4 space-y-3">
                    <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
                      Override the AI provider for individual pipeline agents. Leave as "Use Default" to use the task-level provider.
                    </p>
                    {Object.entries(AGENT_LABELS).map(([agent, label]) => (
                      <div key={agent} className="flex items-center gap-3">
                        <label className="text-sm text-gray-700 dark:text-gray-300 w-40 shrink-0">
                          {label}
                        </label>
                        <select
                          value={(settings.agent_providers || {})[agent] || ''}
                          onChange={(e) => updateAgentProvider(agent, e.target.value)}
                          className="flex-1 px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                        >
                          <option value="">Use Default</option>
                          <option value="gemini">Google Gemini</option>
                          <option value="claude">Anthropic Claude</option>
                          <option value="openai_compat">OpenAI-Compatible Proxy</option>
                          <option value="claude_proxy">Claude Code Proxy</option>
                        </select>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Gemini Settings Section */}
              <div className="border border-gray-200 dark:border-gray-700 rounded-lg">
                <button
                  onClick={() => toggleSection('gemini')}
                  className="w-full flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-750 hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-800 dark:text-gray-200 rounded-t-lg"
                >
                  <span className="font-medium">Gemini Settings</span>
                  {expandedSections.gemini ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </button>
                {expandedSections.gemini && (
                  <div className="p-4 space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Gemini API Key
                      </label>
                      <input
                        type="password"
                        value={settings.gemini_api_key || ''}
                        onChange={(e) => updateSetting('gemini_api_key', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                        placeholder="Enter your Gemini API key"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Model
                      </label>
                      <select
                        value={settings.gemini_model || 'gemini-3-pro-preview'}
                        onChange={(e) => updateSetting('gemini_model', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                      >
                        <option value="gemini-3.1-pro-preview">Gemini 3.1 Pro (Preview)</option>
                        <option value="gemini-3-pro-preview">Gemini 3 Pro (Preview)</option>
                        <option value="gemini-2.5-pro">Gemini 2.5 Pro</option>
                        <option value="gemini-2.5-flash">Gemini 2.5 Flash</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Thinking Level
                      </label>
                      <select
                        value={settings.gemini_thinking_level || 'high'}
                        onChange={(e) => updateSetting('gemini_thinking_level', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                      >
                        <option value="minimal">Minimal (Fastest)</option>
                        <option value="low">Low (Faster)</option>
                        <option value="medium">Medium (Balanced)</option>
                        <option value="high">High (Better Quality)</option>
                      </select>
                    </div>
                    <div className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        id="enable_search"
                        checked={settings.gemini_enable_search || false}
                        onChange={(e) => updateSetting('gemini_enable_search', e.target.checked)}
                        className="w-4 h-4 text-blue-600 rounded"
                      />
                      <label htmlFor="enable_search" className="text-sm text-gray-700 dark:text-gray-300">
                        Enable Google Search Grounding
                      </label>
                    </div>
                  </div>
                )}
              </div>

              {/* Claude Settings Section */}
              <div className="border border-gray-200 dark:border-gray-700 rounded-lg">
                <button
                  onClick={() => toggleSection('claude')}
                  className="w-full flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-750 hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-800 dark:text-gray-200"
                >
                  <span className="font-medium">Claude Settings</span>
                  {expandedSections.claude ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </button>
                {expandedSections.claude && (
                  <div className="p-4 space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Claude API Key
                      </label>
                      <input
                        type="password"
                        value={settings.claude_api_key || ''}
                        onChange={(e) => updateSetting('claude_api_key', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                        placeholder="Enter your Anthropic API key"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Model
                      </label>
                      <select
                        value={settings.claude_model || 'claude-sonnet-4-5-20250929'}
                        onChange={(e) => updateSetting('claude_model', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                      >
                        <option value="claude-sonnet-4-5-20250929">Claude Sonnet 4.5</option>
                        <option value="claude-opus-4-6">Claude Opus 4.6</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Temperature (0.0 - 1.0)
                      </label>
                      <input
                        type="number"
                        step="0.1"
                        min="0"
                        max="1"
                        value={settings.claude_temperature ?? ''}
                        onChange={(e) => updateSetting('claude_temperature', e.target.value ? parseFloat(e.target.value) : null)}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                        placeholder="Leave empty for default (1.0)"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Max Output Tokens
                      </label>
                      <input
                        type="number"
                        value={settings.claude_max_output_tokens ?? ''}
                        onChange={(e) => updateSetting('claude_max_output_tokens', e.target.value ? parseInt(e.target.value) : null)}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                        placeholder="Leave empty for default (16384)"
                      />
                    </div>
                    <div className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        id="claude_extended_thinking"
                        checked={settings.claude_extended_thinking || false}
                        onChange={(e) => updateSetting('claude_extended_thinking', e.target.checked)}
                        className="w-4 h-4 text-blue-600 rounded"
                      />
                      <label htmlFor="claude_extended_thinking" className="text-sm text-gray-700 dark:text-gray-300">
                        Enable Extended Thinking
                      </label>
                    </div>
                    {settings.claude_extended_thinking && (
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                          Thinking Budget (tokens)
                        </label>
                        <input
                          type="number"
                          min="1000"
                          max="128000"
                          value={settings.claude_thinking_budget || 10000}
                          onChange={(e) => updateSetting('claude_thinking_budget', parseInt(e.target.value))}
                          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                        />
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                          Temperature is fixed at 1.0 when extended thinking is enabled
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* OpenAI-Compatible Proxy Settings Section */}
              <div className="border border-gray-200 dark:border-gray-700 rounded-lg">
                <button
                  onClick={() => toggleSection('openai_compat')}
                  className="w-full flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-750 hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-800 dark:text-gray-200"
                >
                  <span className="font-medium">OpenAI-Compatible Proxy</span>
                  {expandedSections.openai_compat ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </button>
                {expandedSections.openai_compat && (
                  <div className="p-4 space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Base URL
                      </label>
                      <input
                        type="text"
                        value={settings.openai_compat_base_url || 'http://localhost:3000/v1'}
                        onChange={(e) => updateSetting('openai_compat_base_url', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                        placeholder="http://localhost:3000/v1"
                      />
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                        Works with Claude Code proxy, Ollama, LM Studio, etc.
                      </p>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        API Key (optional)
                      </label>
                      <input
                        type="password"
                        value={settings.openai_compat_api_key || ''}
                        onChange={(e) => updateSetting('openai_compat_api_key', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                        placeholder="Leave empty if not required"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Model
                      </label>
                      <input
                        type="text"
                        value={settings.openai_compat_model || 'gpt-4o'}
                        onChange={(e) => updateSetting('openai_compat_model', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                        placeholder="Model name (e.g. gpt-4o, llama3, etc.)"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Temperature (0.0 - 2.0)
                      </label>
                      <input
                        type="number"
                        step="0.1"
                        min="0"
                        max="2"
                        value={settings.openai_compat_temperature ?? ''}
                        onChange={(e) => updateSetting('openai_compat_temperature', e.target.value ? parseFloat(e.target.value) : null)}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                        placeholder="Leave empty for default"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Max Output Tokens
                      </label>
                      <input
                        type="number"
                        value={settings.openai_compat_max_output_tokens ?? ''}
                        onChange={(e) => updateSetting('openai_compat_max_output_tokens', e.target.value ? parseInt(e.target.value) : null)}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                        placeholder="Leave empty for default"
                      />
                    </div>
                  </div>
                )}
              </div>

              {/* Claude Code Proxy Settings Section */}
              <div className="border border-gray-200 dark:border-gray-700 rounded-lg">
                <button
                  onClick={() => toggleSection('claude_proxy')}
                  className="w-full flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-750 hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-800 dark:text-gray-200"
                >
                  <span className="font-medium">Claude Code Proxy</span>
                  {expandedSections.claude_proxy ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </button>
                {expandedSections.claude_proxy && (
                  <div className="p-4 space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Base URL
                      </label>
                      <input
                        type="text"
                        value={settings.claude_proxy_base_url || 'http://localhost:42069'}
                        onChange={(e) => updateSetting('claude_proxy_base_url', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                        placeholder="http://localhost:42069"
                      />
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                        URL of the claude-code-proxy (Anthropic API)
                      </p>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        API Key (optional)
                      </label>
                      <input
                        type="password"
                        value={settings.claude_proxy_api_key || ''}
                        onChange={(e) => updateSetting('claude_proxy_api_key', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                        placeholder="Leave empty (proxy handles auth via OAuth)"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Model
                      </label>
                      <select
                        value={settings.claude_proxy_model || 'claude-sonnet-4-5-20250929'}
                        onChange={(e) => updateSetting('claude_proxy_model', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                      >
                        <option value="claude-sonnet-4-5-20250929">Claude Sonnet 4.5 (2025-09-29)</option>
                        <option value="claude-opus-4-6">Claude Opus 4.6</option>
                        <option value="claude-haiku-4-5-20251001">Claude Haiku 4.5 (2025-10-01)</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Temperature (0.0 - 1.0)
                      </label>
                      <input
                        type="number"
                        step="0.1"
                        min="0"
                        max="1"
                        value={settings.claude_proxy_temperature ?? ''}
                        onChange={(e) => updateSetting('claude_proxy_temperature', e.target.value ? parseFloat(e.target.value) : null)}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                        placeholder="Leave empty for default (1.0)"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Max Output Tokens
                      </label>
                      <input
                        type="number"
                        value={settings.claude_proxy_max_output_tokens ?? ''}
                        onChange={(e) => updateSetting('claude_proxy_max_output_tokens', e.target.value ? parseInt(e.target.value) : null)}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                        placeholder="Leave empty for default (16384)"
                      />
                    </div>
                  </div>
                )}
              </div>

              {/* DeepSeek Settings Section */}
              <div className="border border-gray-200 dark:border-gray-700 rounded-lg">
                <button
                  onClick={() => toggleSection('deepseek')}
                  className="w-full flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-750 hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-800 dark:text-gray-200"
                >
                  <span className="font-medium">DeepSeek</span>
                  {expandedSections.deepseek ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </button>
                {expandedSections.deepseek && (
                  <div className="p-4 space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        DeepSeek API Key
                      </label>
                      <input
                        type="password"
                        value={settings.deepseek_api_key || ''}
                        onChange={(e) => updateSetting('deepseek_api_key', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                        placeholder="Enter your DeepSeek API key"
                      />
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                        Get your key at platform.deepseek.com — best Chinese language quality
                      </p>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Model
                      </label>
                      <select
                        value={settings.deepseek_model || 'deepseek-chat'}
                        onChange={(e) => updateSetting('deepseek_model', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                      >
                        <option value="deepseek-chat">DeepSeek V3 (Chat)</option>
                        <option value="deepseek-reasoner">DeepSeek R1 (Reasoner)</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Temperature (0.0 - 2.0)
                      </label>
                      <input
                        type="number"
                        step="0.1"
                        min="0"
                        max="2"
                        value={settings.deepseek_temperature ?? ''}
                        onChange={(e) => updateSetting('deepseek_temperature', e.target.value ? parseFloat(e.target.value) : null)}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                        placeholder="Leave empty for default"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Max Output Tokens
                      </label>
                      <input
                        type="number"
                        value={settings.deepseek_max_output_tokens ?? ''}
                        onChange={(e) => updateSetting('deepseek_max_output_tokens', e.target.value ? parseInt(e.target.value) : null)}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                        placeholder="Leave empty for default"
                      />
                    </div>
                  </div>
                )}
              </div>

              {/* Qwen Settings Section */}
              <div className="border border-gray-200 dark:border-gray-700 rounded-lg">
                <button
                  onClick={() => toggleSection('qwen')}
                  className="w-full flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-750 hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-800 dark:text-gray-200"
                >
                  <span className="font-medium">Qwen (Alibaba)</span>
                  {expandedSections.qwen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </button>
                {expandedSections.qwen && (
                  <div className="p-4 space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Qwen API Key (DashScope)
                      </label>
                      <input
                        type="password"
                        value={settings.qwen_api_key || ''}
                        onChange={(e) => updateSetting('qwen_api_key', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                        placeholder="Enter your DashScope API key"
                      />
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                        Get your key at dashscope.aliyun.com — strong Chinese generation, 1M context
                      </p>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Model
                      </label>
                      <select
                        value={settings.qwen_model || 'qwen-plus'}
                        onChange={(e) => updateSetting('qwen_model', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                      >
                        <option value="qwen-plus">Qwen Plus (Balanced)</option>
                        <option value="qwen-max">Qwen Max (Best Quality)</option>
                        <option value="qwen-turbo">Qwen Turbo (Fastest)</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Temperature (0.0 - 2.0)
                      </label>
                      <input
                        type="number"
                        step="0.1"
                        min="0"
                        max="2"
                        value={settings.qwen_temperature ?? ''}
                        onChange={(e) => updateSetting('qwen_temperature', e.target.value ? parseFloat(e.target.value) : null)}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                        placeholder="Leave empty for default"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Max Output Tokens
                      </label>
                      <input
                        type="number"
                        value={settings.qwen_max_output_tokens ?? ''}
                        onChange={(e) => updateSetting('qwen_max_output_tokens', e.target.value ? parseInt(e.target.value) : null)}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                        placeholder="Leave empty for default"
                      />
                    </div>
                  </div>
                )}
              </div>

              {/* Generation Settings Section */}
              <div className="border border-gray-200 dark:border-gray-700 rounded-lg">
                <button
                  onClick={() => toggleSection('generation')}
                  className="w-full flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-750 hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-800 dark:text-gray-200"
                >
                  <span className="font-medium">Generation Settings</span>
                  {expandedSections.generation ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </button>
                {expandedSections.generation && (
                  <div className="p-4 space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Temperature (0.0 - 2.0)
                      </label>
                      <input
                        type="number"
                        step="0.1"
                        min="0"
                        max="2"
                        value={settings.gemini_temperature ?? ''}
                        onChange={(e) => updateSetting('gemini_temperature', e.target.value ? parseFloat(e.target.value) : null)}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                        placeholder="Leave empty for default (1.0)"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Max Output Tokens
                      </label>
                      <input
                        type="number"
                        value={settings.gemini_max_output_tokens ?? ''}
                        onChange={(e) => updateSetting('gemini_max_output_tokens', e.target.value ? parseInt(e.target.value) : null)}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                        placeholder="Leave empty for default"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Max LaTeX Retries
                      </label>
                      <input
                        type="number"
                        min="1"
                        max="10"
                        value={settings.max_latex_retries || 3}
                        onChange={(e) => updateSetting('max_latex_retries', parseInt(e.target.value))}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                      />
                    </div>
                    {templates.length > 0 && (
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                          Default Resume Template
                        </label>
                        <select
                          value={settings.default_template_id || 'classic'}
                          onChange={(e) => updateSetting('default_template_id', e.target.value)}
                          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                        >
                          {templates.map((t) => (
                            <option key={t.id} value={t.id}>{t.name} - {t.description}</option>
                          ))}
                        </select>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                          Template used for new tasks by default
                        </p>
                      </div>
                    )}
                    <div className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        id="generate_cover_letter"
                        checked={settings.generate_cover_letter !== false}
                        onChange={(e) => updateSetting('generate_cover_letter', e.target.checked)}
                        className="w-4 h-4 text-blue-600 rounded"
                      />
                      <label htmlFor="generate_cover_letter" className="text-sm text-gray-700 dark:text-gray-300">
                        Generate Cover Letter by Default
                      </label>
                    </div>
                  </div>
                )}
              </div>

              {/* Page Validation Section */}
              <div className="border border-gray-200 dark:border-gray-700 rounded-lg">
                <button
                  onClick={() => toggleSection('validation')}
                  className="w-full flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-750 hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-800 dark:text-gray-200"
                >
                  <span className="font-medium">Page Length Validation</span>
                  {expandedSections.validation ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </button>
                {expandedSections.validation && (
                  <div className="p-4 space-y-4">
                    <div className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        id="enforce_resume_one_page"
                        checked={settings.enforce_resume_one_page !== false}
                        onChange={(e) => updateSetting('enforce_resume_one_page', e.target.checked)}
                        className="w-4 h-4 text-blue-600 rounded"
                      />
                      <label htmlFor="enforce_resume_one_page" className="text-sm text-gray-700 dark:text-gray-300">
                        Enforce Resume is 1 Page
                      </label>
                    </div>
                    <div className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        id="enforce_cover_letter_one_page"
                        checked={settings.enforce_cover_letter_one_page !== false}
                        onChange={(e) => updateSetting('enforce_cover_letter_one_page', e.target.checked)}
                        className="w-4 h-4 text-blue-600 rounded"
                      />
                      <label htmlFor="enforce_cover_letter_one_page" className="text-sm text-gray-700 dark:text-gray-300">
                        Enforce Cover Letter is 1 Page
                      </label>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Max Page Retry Attempts
                      </label>
                      <input
                        type="number"
                        min="1"
                        max="10"
                        value={settings.max_page_retry_attempts || 3}
                        onChange={(e) => updateSetting('max_page_retry_attempts', parseInt(e.target.value))}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                      />
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                        Number of times to retry if document exceeds 1 page
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500 dark:text-gray-400">
              Failed to load settings
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-750">
          <button
            onClick={resetSettings}
            className="px-4 py-2 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg flex items-center gap-2"
          >
            <RefreshCw className="w-4 h-4" />
            Reset to Defaults
          </button>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300"
            >
              Cancel
            </button>
            <button
              onClick={saveSettings}
              disabled={saving}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
            >
              <Save className="w-4 h-4" />
              {saving ? 'Saving...' : 'Save Settings'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
