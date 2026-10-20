import React from 'react';
import { Sparkles, Layers, Flame, FolderOpen, Loader2 } from 'lucide-react';

interface ActionButtonsProps {
  onTranscribe: () => void;
  onSoftMux: () => void;
  onHardBurn: () => void;
  onOpenOutput: () => void;
  hasVideo: boolean;
  hasSegments: boolean;
  isProcessing: boolean;
}

export const ActionButtons: React.FC<ActionButtonsProps> = ({
  onTranscribe,
  onSoftMux,
  onHardBurn,
  onOpenOutput,
  hasVideo,
  hasSegments,
  isProcessing,
}) => {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
      {/* 1. Primary: Transcribe & Translate */}
      <button
        type="button"
        onClick={onTranscribe}
        disabled={!hasVideo || isProcessing}
        className={`relative overflow-hidden group flex items-center justify-center gap-2.5 px-5 py-3 rounded-xl font-medium text-sm transition-all duration-300 ${
          !hasVideo || isProcessing
            ? 'bg-surface-card border border-border-card text-content-dim cursor-not-allowed opacity-60'
            : 'bg-gradient-to-r from-brand-indigo via-indigo-500 to-brand-indigo-hover text-white shadow-glow-indigo hover:shadow-lg hover:scale-[1.01] active:scale-[0.99] border border-brand-indigo/50'
        }`}
      >
        {isProcessing ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin text-white" />
            <span>Processing...</span>
          </>
        ) : (
          <>
            <Sparkles className="w-4 h-4 text-brand-cyan group-hover:rotate-12 transition-transform duration-300" />
            <span>Transcribe</span>
          </>
        )}
      </button>

      {/* 2. Secondary: Soft Sub */}
      <button
        type="button"
        onClick={onSoftMux}
        disabled={!hasVideo || !hasSegments || isProcessing}
        className={`flex items-center justify-center gap-2.5 px-4 py-3 rounded-xl font-medium text-sm transition-all duration-300 ${
          !hasVideo || !hasSegments || isProcessing
            ? 'bg-surface-card border border-border-card text-content-dim cursor-not-allowed opacity-60'
            : 'bg-brand-cyan/15 text-brand-cyan border border-brand-cyan/35 hover:bg-brand-cyan/25 hover:shadow-glow-cyan active:scale-[0.99]'
        }`}
        title="Mux subtitle stream losslessly into video container"
      >
        <Layers className="w-4 h-4 text-brand-cyan" />
        <span>Soft Sub</span>
      </button>

      {/* 3. Tertiary: Burn Sub */}
      <button
        type="button"
        onClick={onHardBurn}
        disabled={!hasVideo || !hasSegments || isProcessing}
        className={`flex items-center justify-center gap-2.5 px-4 py-3 rounded-xl font-medium text-sm transition-all duration-300 ${
          !hasVideo || !hasSegments || isProcessing
            ? 'bg-surface-card border border-border-card text-content-dim cursor-not-allowed opacity-60'
            : 'bg-brand-rose hover:bg-brand-rose-hover text-white shadow-sm hover:shadow-lg active:scale-[0.99]'
        }`}
        title="Hardcode subtitles permanently into video"
      >
        <Flame className="w-4 h-4 text-white" />
        <span>Burn Sub</span>
      </button>

      {/* 4. Open Output Folder */}
      <button
        type="button"
        onClick={onOpenOutput}
        className="flex items-center justify-center gap-2 px-4 py-3 rounded-xl font-medium text-sm bg-brand-emerald-bg text-brand-emerald border border-brand-emerald/30 hover:bg-brand-emerald/20 transition-all duration-200 active:scale-[0.99]"
        title="Open output folder"
      >
        <FolderOpen className="w-4 h-4 text-brand-emerald" />
        <span>Open Folder</span>
      </button>
    </div>
  );
};
