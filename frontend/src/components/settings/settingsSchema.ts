import type { SettingsSection } from './SettingFieldRenderer';

const PROVIDER_OPTIONS = [
  { value: 'gemini', label: 'Google Gemini' },
  { value: 'claude', label: 'Anthropic Claude' },
  { value: 'openai_compat', label: 'OpenAI-Compatible Proxy' },
  { value: 'claude_proxy', label: 'Claude Code Proxy' },
  { value: 'deepseek', label: 'DeepSeek' },
  { value: 'qwen', label: 'Qwen (Alibaba)' },
];

const AGENT_PROVIDER_OPTIONS = [
  { value: '', label: 'Use Default' },
  { value: 'gemini', label: 'Google Gemini' },
  { value: 'claude', label: 'Anthropic Claude' },
  { value: 'openai_compat', label: 'OpenAI-Compatible Proxy' },
  { value: 'claude_proxy', label: 'Claude Code Proxy' },
];

export const SETTINGS_SECTIONS: SettingsSection[] = [
  {
    id: 'provider',
    title: 'Default AI Provider',
    defaultExpanded: true,
    fields: [
      {
        key: 'default_provider',
        label: 'Default Provider',
        type: 'select',
        options: PROVIDER_OPTIONS,
        helpText: 'Provider used for new tasks by default. Individual tasks can override this.',
      },
    ],
  },
  {
    id: 'gemini',
    title: 'Gemini Settings',
    defaultExpanded: true,
    fields: [
      {
        key: 'gemini_api_key',
        label: 'Gemini API Key',
        type: 'password',
        placeholder: 'Enter your Gemini API key',
      },
      {
        key: 'gemini_model',
        label: 'Model',
        type: 'select',
        options: [
          { value: 'gemini-3.1-pro-preview', label: 'Gemini 3.1 Pro (Preview)' },
          { value: 'gemini-3-pro-preview', label: 'Gemini 3 Pro (Preview)' },
          { value: 'gemini-2.5-pro', label: 'Gemini 2.5 Pro' },
          { value: 'gemini-2.5-flash', label: 'Gemini 2.5 Flash' },
        ],
      },
      {
        key: 'gemini_thinking_level',
        label: 'Thinking Level',
        type: 'select',
        options: [
          { value: 'minimal', label: 'Minimal (Fastest)' },
          { value: 'low', label: 'Low (Faster)' },
          { value: 'medium', label: 'Medium (Balanced)' },
          { value: 'high', label: 'High (Better Quality)' },
        ],
      },
      { key: 'gemini_enable_search', label: 'Enable Google Search Grounding', type: 'toggle' },
    ],
  },
  {
    id: 'claude',
    title: 'Claude Settings',
    fields: [
      {
        key: 'claude_api_key',
        label: 'Claude API Key',
        type: 'password',
        placeholder: 'Enter your Anthropic API key',
      },
      {
        key: 'claude_model',
        label: 'Model',
        type: 'select',
        options: [
          { value: 'claude-sonnet-4-5-20250929', label: 'Claude Sonnet 4.5' },
          { value: 'claude-opus-4-6', label: 'Claude Opus 4.6' },
        ],
      },
      {
        key: 'claude_temperature',
        label: 'Temperature (0.0 - 1.0)',
        type: 'number',
        step: 0.1,
        min: 0,
        max: 1,
        placeholder: 'Leave empty for default (1.0)',
      },
      {
        key: 'claude_max_output_tokens',
        label: 'Max Output Tokens',
        type: 'number',
        placeholder: 'Leave empty for default (16384)',
      },
      { key: 'claude_extended_thinking', label: 'Enable Extended Thinking', type: 'toggle' },
      {
        key: 'claude_thinking_budget',
        label: 'Thinking Budget (tokens)',
        type: 'number',
        min: 1000,
        max: 128000,
        helpText: 'Temperature is fixed at 1.0 when extended thinking is enabled',
        conditional: (s) => s.claude_extended_thinking,
      },
    ],
  },
  {
    id: 'openai_compat',
    title: 'OpenAI-Compatible Proxy',
    fields: [
      {
        key: 'openai_compat_base_url',
        label: 'Base URL',
        type: 'text',
        placeholder: 'http://localhost:3000/v1',
        helpText: 'Works with Claude Code proxy, Ollama, LM Studio, etc.',
      },
      {
        key: 'openai_compat_api_key',
        label: 'API Key (optional)',
        type: 'password',
        placeholder: 'Leave empty if not required',
      },
      {
        key: 'openai_compat_model',
        label: 'Model',
        type: 'text',
        placeholder: 'Model name (e.g. gpt-4o, llama3, etc.)',
      },
      {
        key: 'openai_compat_temperature',
        label: 'Temperature (0.0 - 2.0)',
        type: 'number',
        step: 0.1,
        min: 0,
        max: 2,
        placeholder: 'Leave empty for default',
      },
      {
        key: 'openai_compat_max_output_tokens',
        label: 'Max Output Tokens',
        type: 'number',
        placeholder: 'Leave empty for default',
      },
    ],
  },
  {
    id: 'claude_proxy',
    title: 'Claude Code Proxy',
    fields: [
      {
        key: 'claude_proxy_base_url',
        label: 'Base URL',
        type: 'text',
        placeholder: 'http://localhost:42069',
        helpText: 'URL of the claude-code-proxy (Anthropic API)',
      },
      {
        key: 'claude_proxy_api_key',
        label: 'API Key (optional)',
        type: 'password',
        placeholder: 'Leave empty (proxy handles auth via OAuth)',
      },
      {
        key: 'claude_proxy_model',
        label: 'Model',
        type: 'select',
        options: [
          { value: 'claude-sonnet-4-5-20250929', label: 'Claude Sonnet 4.5 (2025-09-29)' },
          { value: 'claude-opus-4-6', label: 'Claude Opus 4.6' },
          { value: 'claude-haiku-4-5-20251001', label: 'Claude Haiku 4.5 (2025-10-01)' },
        ],
      },
      {
        key: 'claude_proxy_temperature',
        label: 'Temperature (0.0 - 1.0)',
        type: 'number',
        step: 0.1,
        min: 0,
        max: 1,
        placeholder: 'Leave empty for default (1.0)',
      },
      {
        key: 'claude_proxy_max_output_tokens',
        label: 'Max Output Tokens',
        type: 'number',
        placeholder: 'Leave empty for default (16384)',
      },
    ],
  },
  {
    id: 'deepseek',
    title: 'DeepSeek',
    fields: [
      {
        key: 'deepseek_api_key',
        label: 'DeepSeek API Key',
        type: 'password',
        placeholder: 'Enter your DeepSeek API key',
        helpText: 'Get your key at platform.deepseek.com -- best Chinese language quality',
      },
      {
        key: 'deepseek_model',
        label: 'Model',
        type: 'select',
        options: [
          { value: 'deepseek-chat', label: 'DeepSeek V3 (Chat)' },
          { value: 'deepseek-reasoner', label: 'DeepSeek R1 (Reasoner)' },
        ],
      },
      {
        key: 'deepseek_temperature',
        label: 'Temperature (0.0 - 2.0)',
        type: 'number',
        step: 0.1,
        min: 0,
        max: 2,
        placeholder: 'Leave empty for default',
      },
      {
        key: 'deepseek_max_output_tokens',
        label: 'Max Output Tokens',
        type: 'number',
        placeholder: 'Leave empty for default',
      },
    ],
  },
  {
    id: 'qwen',
    title: 'Qwen (Alibaba)',
    fields: [
      {
        key: 'qwen_api_key',
        label: 'Qwen API Key (DashScope)',
        type: 'password',
        placeholder: 'Enter your DashScope API key',
        helpText: 'Get your key at dashscope.aliyun.com -- strong Chinese generation, 1M context',
      },
      {
        key: 'qwen_model',
        label: 'Model',
        type: 'select',
        options: [
          { value: 'qwen-plus', label: 'Qwen Plus (Balanced)' },
          { value: 'qwen-max', label: 'Qwen Max (Best Quality)' },
          { value: 'qwen-turbo', label: 'Qwen Turbo (Fastest)' },
        ],
      },
      {
        key: 'qwen_temperature',
        label: 'Temperature (0.0 - 2.0)',
        type: 'number',
        step: 0.1,
        min: 0,
        max: 2,
        placeholder: 'Leave empty for default',
      },
      {
        key: 'qwen_max_output_tokens',
        label: 'Max Output Tokens',
        type: 'number',
        placeholder: 'Leave empty for default',
      },
    ],
  },
  {
    id: 'generation',
    title: 'Generation Settings',
    defaultExpanded: true,
    fields: [
      {
        key: 'gemini_temperature',
        label: 'Temperature (0.0 - 2.0)',
        type: 'number',
        step: 0.1,
        min: 0,
        max: 2,
        placeholder: 'Leave empty for default (1.0)',
      },
      {
        key: 'gemini_max_output_tokens',
        label: 'Max Output Tokens',
        type: 'number',
        placeholder: 'Leave empty for default',
      },
      { key: 'max_latex_retries', label: 'Max LaTeX Retries', type: 'number', min: 1, max: 10 },
      { key: 'generate_cover_letter', label: 'Generate Cover Letter by Default', type: 'toggle' },
      {
        key: 'allow_ai_fabrication',
        label: 'Allow AI Fabrication',
        type: 'toggle',
        helpText:
          'When disabled, AI will only use facts explicitly stated in your profile. No invented metrics or skills.',
      },
    ],
  },
  {
    id: 'validation',
    title: 'Page Length Validation',
    defaultExpanded: true,
    fields: [
      { key: 'enforce_resume_one_page', label: 'Enforce Resume is 1 Page', type: 'toggle' },
      {
        key: 'enforce_cover_letter_one_page',
        label: 'Enforce Cover Letter is 1 Page',
        type: 'toggle',
      },
      {
        key: 'max_page_retry_attempts',
        label: 'Max Page Retry Attempts',
        type: 'number',
        min: 1,
        max: 10,
        helpText: 'Number of times to retry if document exceeds 1 page',
      },
    ],
  },
  {
    id: 'resume_validation',
    title: 'Resume Validation',
    fields: [
      {
        key: 'enable_contact_replacement',
        label: 'Auto-fix Contact Info',
        type: 'toggle',
        helpText:
          'Directly replace the resume header with your parsed contact info. Prevents wrong name/email/phone.',
      },
      {
        key: 'enable_text_validation',
        label: 'Text Validation',
        type: 'toggle',
        helpText:
          'Verify that your name, email, and phone appear correctly in the LaTeX source. Detects placeholder text.',
      },
      {
        key: 'enable_llm_validation',
        label: 'LLM Validation',
        type: 'toggle',
        helpText:
          'AI reviews the entire resume for accuracy, fabricated content, and formatting issues. Slower and uses an extra API call.',
      },
    ],
  },
  {
    id: 'profile',
    title: 'User Profile Links',
    fields: [
      {
        key: 'user_linkedin_url',
        label: 'LinkedIn URL',
        type: 'url',
        placeholder: 'https://linkedin.com/in/yourprofile',
      },
      {
        key: 'user_github_url',
        label: 'GitHub URL',
        type: 'url',
        placeholder: 'https://github.com/yourusername',
      },
    ],
  },
];

export const AGENT_LABELS: Record<string, string> = {
  jd_analyzer: 'JD Analyzer',
  relevance_matcher: 'Relevance Matcher',
  resume_writer: 'Resume Writer',
  cover_letter_writer: 'Cover Letter Writer',
  company_researcher: 'Company Researcher',
};

export { AGENT_PROVIDER_OPTIONS };
