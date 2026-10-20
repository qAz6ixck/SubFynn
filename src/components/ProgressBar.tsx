import React from 'react';
import { motion } from 'framer-motion';
import { Loader2, CheckCircle2, Activity } from 'lucide-react';
import { PipelineProgress } from '../types/subtitle';

interface ProgressBarProps {
  progress: PipelineProgress;
  isProcessing: boolean;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({ progress, isProcessing }) => {
  const percent = Math.max(0, Math.min(100, progress.percent || 0));
  const isComplete = percent >= 100 && !isProcessing;

  if (!isProcessing && percent === 0) {
    return null;
  }

  return (
    <div className="glass-card glass-card-specular p-4 transition-all duration-300">
      <div className="flex items-center justify-between text-xs mb-2">
        <div className="flex items-center gap-2 font-medium text-content-white truncate max-w-[80%]">
          {isProcessing ? (
            <Loader2 className="w-4 h-4 text-brand-cyan animate-spin shrink-0" />
          ) : isComplete ? (
            <CheckCircle2 className="w-4 h-4 text-brand-emerald shrink-0" />
          ) : (
            <Activity className="w-4 h-4 text-brand-indigo shrink-0" />
          )}
          <span className="truncate">{progress.message || 'Processing...'}</span>
          {progress.stage && (
            <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-surface-input border border-border-card text-brand-cyan uppercase tracking-wider shrink-0">
              {progress.stage}
            </span>
          )}
        </div>

        <span className="font-mono font-bold text-sm text-brand-cyan shrink-0">
          {Math.round(percent)}%
        </span>
      </div>

      {/* Dual-tier Glowing Progress Bar */}
      <div className="w-full h-2.5 bg-surface-input rounded-full overflow-hidden border border-border-glass relative p-[1px]">
        {/* Glow backdrop layer */}
        <div
          className="absolute inset-0 bg-gradient-to-r from-brand-indigo/30 via-brand-cyan/30 to-brand-pink/30 blur-sm pointer-events-none"
          style={{ width: `${percent}%` }}
        />
        {/* Active Fill Track */}
        <motion.div
          className="h-full bg-gradient-to-r from-brand-indigo via-brand-cyan to-brand-pink rounded-full relative overflow-hidden"
          initial={{ width: '0%' }}
          animate={{ width: `${percent}%` }}
          transition={{ duration: 0.3, ease: 'easeOut' }}
        >
          {/* Shimmer Light Bar */}
          {isProcessing && (
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent -translate-x-full animate-[shimmer_1.5s_infinite]" />
          )}
        </motion.div>
      </div>
    </div>
  );
};
