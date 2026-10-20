import React, { useState } from 'react';
import {
  Clock,
  RotateCcw,
  RotateCw,
  Plus,
  ArrowRightLeft,
} from 'lucide-react';

interface TimeShiftControlsProps {
  onApplyShift: (offsetSeconds: number) => void;
  onAddSegment: () => void;
  canUndo: boolean;
  canRedo: boolean;
  onUndo: () => void;
  onRedo: () => void;
  totalSegments: number;
  disabled?: boolean;
}

export const TimeShiftControls: React.FC<TimeShiftControlsProps> = ({
  onApplyShift,
  onAddSegment,
  canUndo,
  canRedo,
  onUndo,
  onRedo,
  totalSegments,
  disabled = false,
}) => {
  const [customOffset, setCustomOffset] = useState<string>('');

  const handleCustomApply = (e: React.FormEvent) => {
    e.preventDefault();
    const val = parseFloat(customOffset);
    if (!isNaN(val) && val !== 0) {
      onApplyShift(val);
      setCustomOffset('');
    }
  };

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-surface-card rounded-xl border border-border-card text-xs">
      {/* Quick Time Shift Pills */}
      <div className="flex items-center gap-1.5 flex-wrap">
        <span className="text-content-dim font-medium mr-1 flex items-center gap-1">
          <Clock className="w-3.5 h-3.5 text-brand-indigo" />
          Time Shift:
        </span>

        <button
          type="button"
          onClick={() => onApplyShift(-1.0)}
          disabled={disabled || totalSegments === 0}
          className="px-2.5 py-1 rounded-lg bg-surface-input hover:bg-surface-dropdown border border-border-input text-content-muted hover:text-white transition-colors disabled:opacity-40 disabled:cursor-not-allowed font-mono"
          title="Shift all subtitles 1.0s earlier"
        >
          -1.0s
        </button>

        <button
          type="button"
          onClick={() => onApplyShift(-0.5)}
          disabled={disabled || totalSegments === 0}
          className="px-2.5 py-1 rounded-lg bg-surface-input hover:bg-surface-dropdown border border-border-input text-content-muted hover:text-white transition-colors disabled:opacity-40 disabled:cursor-not-allowed font-mono"
          title="Shift all subtitles 0.5s earlier"
        >
          -0.5s
        </button>

        <button
          type="button"
          onClick={() => onApplyShift(0.5)}
          disabled={disabled || totalSegments === 0}
          className="px-2.5 py-1 rounded-lg bg-surface-input hover:bg-surface-dropdown border border-border-input text-content-muted hover:text-white transition-colors disabled:opacity-40 disabled:cursor-not-allowed font-mono"
          title="Shift all subtitles 0.5s later"
        >
          +0.5s
        </button>

        <button
          type="button"
          onClick={() => onApplyShift(1.0)}
          disabled={disabled || totalSegments === 0}
          className="px-2.5 py-1 rounded-lg bg-surface-input hover:bg-surface-dropdown border border-border-input text-content-muted hover:text-white transition-colors disabled:opacity-40 disabled:cursor-not-allowed font-mono"
          title="Shift all subtitles 1.0s later"
        >
          +1.0s
        </button>

        {/* Custom Offset Form */}
        <form onSubmit={handleCustomApply} className="flex items-center gap-1 ml-1">
          <div className="relative">
            <input
              type="text"
              value={customOffset}
              onChange={(e) => setCustomOffset(e.target.value)}
              disabled={disabled || totalSegments === 0}
              placeholder="±X.XXX"
              className="w-16 bg-surface-input border border-border-input rounded-lg px-2 py-1 text-xs text-content-white placeholder-content-dim focus:outline-none focus:border-brand-indigo font-mono text-center"
            />
          </div>
          <button
            type="submit"
            disabled={disabled || totalSegments === 0 || !customOffset}
            className="px-2 py-1 rounded-lg bg-brand-indigo/20 hover:bg-brand-indigo/35 border border-brand-indigo/40 text-brand-cyan hover:text-white transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            title="Apply custom time shift in seconds"
          >
            <ArrowRightLeft className="w-3 h-3" />
          </button>
        </form>
      </div>

      {/* Undo / Redo & Add Segment Actions */}
      <div className="flex items-center gap-1.5">
        <button
          type="button"
          onClick={onUndo}
          disabled={!canUndo || disabled}
          className="p-1.5 rounded-lg bg-surface-input hover:bg-surface-dropdown border border-border-input text-content-muted hover:text-white transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
          title="Undo (Ctrl+Z)"
        >
          <RotateCcw className="w-3.5 h-3.5" />
        </button>

        <button
          type="button"
          onClick={onRedo}
          disabled={!canRedo || disabled}
          className="p-1.5 rounded-lg bg-surface-input hover:bg-surface-dropdown border border-border-input text-content-muted hover:text-white transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
          title="Redo (Ctrl+Y)"
        >
          <RotateCw className="w-3.5 h-3.5" />
        </button>

        <div className="w-[1px] h-4 bg-border-card mx-1" />

        <button
          type="button"
          onClick={onAddSegment}
          disabled={disabled}
          className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-brand-emerald-bg text-brand-emerald border border-brand-emerald/30 hover:bg-brand-emerald/20 transition-colors font-medium"
          title="Add a new subtitle segment"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>Add Segment</span>
        </button>
      </div>
    </div>
  );
};
