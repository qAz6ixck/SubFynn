import React, { useState } from 'react';
import { Mic, Bot, Sparkles, Languages, Key, Eye, EyeOff } from 'lucide-react';
import { ModelConfig, WhisperModel, GeminiModel, TranslationStyle, AudioLanguage } from '../types/subtitle';

interface ModelControlsProps {
  config: ModelConfig;
  onChange: (updates: Partial<ModelConfig>) => void;
  disabled?: boolean;
}

export const ModelControls: React.FC<ModelControlsProps> = ({
  config,
  onChange,
  disabled = false,
}) => {
  const [showApiKey, setShowApiKey] = useState<boolean>(false);

  return (
    <div className="glass-card glass-card-specular p-5">
      <div className="flex items-center justify-between mb-4 pb-3 border-b border-border-glass">
        <h2 className="text-sm font-semibold tracking-wide text-content-white uppercase flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-brand-indigo" />
          AI Settings
        </h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* 1. Whisper STT Model */}
        <div>
          <label className="block text-xs font-medium text-content-muted mb-1.5 flex items-center gap-1.5">
            <Mic className="w-3.5 h-3.5 text-brand-cyan" />
            Speech Model
          </label>
          <select
            value={config.whisperModel}
            onChange={(e) => onChange({ whisperModel: e.target.value as WhisperModel })}
            disabled={disabled}
            className="w-full bg-surface-input border border-border-input rounded-xl px-3 py-2 text-xs text-content-white focus:outline-none focus:border-brand-indigo focus:ring-1 focus:ring-brand-indigo transition-all font-sans"
          >
            <option value="large-v3">Whisper Large-v3 (Accurate)</option>
            <option value="base">Whisper Base (Fastest)</option>
            <option value="small">Whisper Small</option>
            <option value="medium">Whisper Medium</option>
            <option value="large-v2">Whisper Large-v2</option>
          </select>
        </div>

        {/* 2. Specialized Gemini Translation Models */}
        <div>
          <label className="block text-xs font-medium text-content-muted mb-1.5 flex items-center gap-1.5">
            <Bot className="w-3.5 h-3.5 text-brand-indigo" />
            Translation Model
          </label>
          <select
            value={config.geminiModel}
            onChange={(e) => onChange({ geminiModel: e.target.value as GeminiModel })}
            disabled={disabled}
            className="w-full bg-surface-input border border-border-input rounded-xl px-3 py-2 text-xs text-content-white focus:outline-none focus:border-brand-indigo focus:ring-1 focus:ring-brand-indigo transition-all font-sans"
          >
            <option value="gemini-3.5-live-translate-preview">
              Gemini Live (Default)
            </option>
            <option value="cloud-translation-llm">
              Translation LLM (Nuanced)
            </option>
            <option value="gemini-2.5-flash">
              Gemini 2.5 Flash (Fast)
            </option>
          </select>
        </div>

        {/* 3. Translation Style */}
        <div>
          <label className="block text-xs font-medium text-content-muted mb-1.5 flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-brand-pink" />
            Translation Style
          </label>
          <select
            value={config.translationStyle}
            onChange={(e) => onChange({ translationStyle: e.target.value as TranslationStyle })}
            disabled={disabled}
            className="w-full bg-surface-input border border-border-input rounded-xl px-3 py-2 text-xs text-content-white focus:outline-none focus:border-brand-indigo focus:ring-1 focus:ring-brand-indigo transition-all font-sans"
          >
            <option value="jav_dirty">Adult (18+ Dirty Talk / Raw)</option>
            <option value="jav">Adult (18+ Standard)</option>
            <option value="jav_sweet">Adult (18+ Sweet & Sensual)</option>
            <option value="general">General Cinema</option>
            <option value="anime">Anime & Series</option>
          </select>
        </div>

        {/* 4. Audio Source Language */}
        <div>
          <label className="block text-xs font-medium text-content-muted mb-1.5 flex items-center gap-1.5">
            <Languages className="w-3.5 h-3.5 text-brand-emerald" />
            Audio Language
          </label>
          <select
            value={config.audioLanguage}
            onChange={(e) => onChange({ audioLanguage: e.target.value as AudioLanguage })}
            disabled={disabled}
            className="w-full bg-surface-input border border-border-input rounded-xl px-3 py-2 text-xs text-content-white focus:outline-none focus:border-brand-indigo focus:ring-1 focus:ring-brand-indigo transition-all font-sans"
          >
            <option value="ja">Japanese (ja)</option>
            <option value="auto">Auto Detect</option>
            <option value="en">English (en)</option>
            <option value="zh">Chinese (zh)</option>
            <option value="ko">Korean (ko)</option>
            <option value="th">Thai (th)</option>
          </select>
        </div>
      </div>

      {/* Gemini API Key Row */}
      <div className="mt-4 pt-3 border-t border-border-glass flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <label className="text-xs font-medium text-content-muted flex items-center gap-1.5 shrink-0">
          <Key className="w-3.5 h-3.5 text-brand-cyan" />
          API Key:
        </label>
        <div className="relative w-full sm:max-w-md">
          <input
            type={showApiKey ? 'text' : 'password'}
            value={config.geminiApiKey}
            onChange={(e) => onChange({ geminiApiKey: e.target.value })}
            disabled={disabled}
            placeholder="AIzaSy... (optional if set in environment)"
            className="w-full bg-surface-input border border-border-input rounded-xl pl-3 pr-10 py-1.5 text-xs text-content-white placeholder-content-dim focus:outline-none focus:border-brand-indigo focus:ring-1 focus:ring-brand-indigo font-mono"
          />
          <button
            type="button"
            onClick={() => setShowApiKey(!showApiKey)}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 text-content-dim hover:text-content-white transition-colors p-0.5"
            title={showApiKey ? 'Hide API Key' : 'Show API Key'}
          >
            {showApiKey ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>
    </div>
  );
};
