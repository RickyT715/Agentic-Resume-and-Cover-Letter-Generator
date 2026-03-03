import { useState, useEffect, useCallback } from 'react';
import { Settings, Save, RefreshCw, X, ChevronDown, ChevronUp } from 'lucide-react';
import { useTaskStore } from '../store/taskStore';
import { AppSettings, Template } from '../types/task';
import { useTemplatesQuery } from '../hooks/useTaskQuery';
import { SettingFieldRenderer } from './settings/SettingFieldRenderer';
import { SETTINGS_SECTIONS } from './settings/settingsSchema';
import { AgentProviders } from './settings/AgentProviders';

interface SettingsPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

export function SettingsPanel({ isOpen, onClose }: SettingsPanelProps) {
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const addToast = useTaskStore((state) => state.addToast);

  const { data: templates = [] } = useTemplatesQuery();

  const defaultExpanded = Object.fromEntries(
    SETTINGS_SECTIONS.map((s) => [s.id, s.defaultExpanded ?? false]),
  );
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    ...defaultExpanded,
    agent_providers: false,
  });

  const loadSettings = useCallback(async () => {
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
  }, [addToast]);

  useEffect(() => {
    if (isOpen) {
      loadSettings();
    }
  }, [isOpen, loadSettings]);

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

  const toggleSection = (section: string) => {
    setExpandedSections((prev) => ({ ...prev, [section]: !prev[section] }));
  };

  const updateSetting = (key: string, value: unknown) => {
    setSettings((prev) => (prev ? ({ ...prev, [key]: value } as AppSettings) : null));
  };

  const updateAgentProvider = (agent: string, provider: string) => {
    setSettings((prev) => {
      if (!prev) return null;
      const current = prev.agent_providers || {};
      return { ...prev, agent_providers: { ...current, [agent]: provider } };
    });
  };

  if (!isOpen) return null;

  // Build the generation section with templates dynamically included
  const renderSection = (section: (typeof SETTINGS_SECTIONS)[number]) => {
    const isExpanded = expandedSections[section.id] ?? false;

    // Filter fields by conditional
    const visibleFields = section.fields.filter(
      (f) => !f.conditional || (settings && f.conditional(settings)),
    );

    return (
      <div key={section.id} className="border border-gray-200 dark:border-gray-700 rounded-lg">
        <button
          onClick={() => toggleSection(section.id)}
          className="w-full flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-750 hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-800 dark:text-gray-200 rounded-t-lg"
        >
          <span className="font-medium">{section.title}</span>
          {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
        {isExpanded && settings && (
          <div className="p-4 space-y-4">
            {visibleFields.map((field) => (
              <SettingFieldRenderer
                key={field.key}
                field={field}
                value={(settings as unknown as Record<string, unknown>)[field.key]}
                onChange={updateSetting}
              />
            ))}
            {/* Special: template selector in generation section */}
            {section.id === 'generation' && templates.length > 0 && (
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Default Resume Template
                </label>
                <select
                  value={settings.default_template_id || 'classic'}
                  onChange={(e) => updateSetting('default_template_id', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                >
                  {templates.map((t: Template) => (
                    <option key={t.id} value={t.id}>
                      {t.name} - {t.description}
                    </option>
                  ))}
                </select>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  Template used for new tasks by default
                </p>
              </div>
            )}
            {/* Special: resume validation description */}
            {section.id === 'resume_validation' && (
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Validate and fix contact information in generated resumes. Enable any combination of
                methods.
              </p>
            )}
            {/* Special: profile description */}
            {section.id === 'profile' && (
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Set your correct LinkedIn and GitHub URLs. The link checker will auto-fix any
                AI-generated URLs to match these.
              </p>
            )}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-750">
          <div className="flex items-center gap-2">
            <Settings className="w-5 h-5 text-gray-600 dark:text-gray-400" />
            <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100">
              Application Settings
            </h2>
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
              {SETTINGS_SECTIONS.map(renderSection)}

              {/* Per-Agent Provider Overrides (special section) */}
              <div className="border border-gray-200 dark:border-gray-700 rounded-lg">
                <button
                  onClick={() => toggleSection('agent_providers')}
                  className="w-full flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-750 hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-800 dark:text-gray-200 rounded-t-lg"
                >
                  <span className="font-medium">Per-Agent Provider Overrides</span>
                  {expandedSections.agent_providers ? (
                    <ChevronUp className="w-4 h-4" />
                  ) : (
                    <ChevronDown className="w-4 h-4" />
                  )}
                </button>
                {expandedSections.agent_providers && (
                  <AgentProviders settings={settings} onUpdate={updateAgentProvider} />
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

export default SettingsPanel;
