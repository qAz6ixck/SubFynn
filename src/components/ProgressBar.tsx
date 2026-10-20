import React from 'react';
import { Loader2, CheckCircle2, Activity } from 'lucide-react';
import { Progress } from '@/components/ui/progress';
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

  // Translate stage code to human-readable Thai label if desired
  const stageLabels: Record<string, string> = {
    idle: 'พร้อมทำงาน',
    demuxing: 'แยกเสียง',
    extracting_audio: 'แยกเสียง',
    transcribing: 'ถอดเสียง',
    translating: 'แปลภาษาไทย',
    generating_subtitles: 'สร้างไฟล์ซับ',
    muxing: 'ฝังซับไตเติล',
    burning: 'เบิร์นซับไตเติล',
    embedding_subtitles: 'ใส่คลิป',
    complete: 'เสร็จสิ้น',
  };

  const currentStageLabel = progress.stage ? (stageLabels[progress.stage] || progress.stage) : '';

  return (
    <div className="glass-card glass-card-specular p-4.5 transition-all duration-300">
      {/* Top Status & Message Row */}
      <div className="flex items-center justify-between text-xs mb-3">
        <div className="flex items-center gap-2.5 font-medium text-content-white truncate max-w-[80%]">
          {isProcessing ? (
            <Loader2 className="w-4 h-4 text-brand-cyan animate-spin shrink-0" />
          ) : isComplete ? (
            <CheckCircle2 className="w-4 h-4 text-brand-emerald shrink-0" />
          ) : (
            <Activity className="w-4 h-4 text-brand-indigo shrink-0" />
          )}

          {/* Real-time step description */}
          <span className="truncate text-xs sm:text-sm text-content-white font-medium">
            {progress.message || 'กำลังประมวลผล...'}
          </span>

          {currentStageLabel && (
            <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-surface-input border border-border-card text-brand-cyan uppercase tracking-wider shrink-0">
              {currentStageLabel}
            </span>
          )}
        </div>

        {/* Percentage Badge */}
        <div className="flex items-center gap-1 shrink-0 font-mono font-bold text-sm text-brand-cyan bg-surface-input/80 px-2.5 py-0.5 rounded-lg border border-border-card">
          <span>{Math.round(percent)}</span>
          <span className="text-xs text-brand-cyan/70">%</span>
        </div>
      </div>

      {/* shadcn/ui style Progress Bar with Sleek Track */}
      <div className="relative">
        <Progress value={percent} className="h-2.5 bg-surface-input/90 shadow-inner" />
        {isProcessing && (
          <div className="absolute inset-0 rounded-full overflow-hidden pointer-events-none">
            <div className="w-full h-full bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full animate-[shimmer_1.8s_infinite]" />
          </div>
        )}
      </div>
    </div>
  );
};
