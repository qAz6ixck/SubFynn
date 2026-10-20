import React, { useState } from 'react';
import {
  Search,
  Download,
  Copy,
  Check,
  FileText,
  X,
  Languages,
} from 'lucide-react';
import { SubtitleSegment } from '../types/subtitle';
import { SubtitleRow } from './SubtitleRow';
import { TimeShiftControls } from './TimeShiftControls';

interface SubtitleEditorProps {
  segments: SubtitleSegment[];
  filteredSegments: SubtitleSegment[];
  searchQuery: string;
  onSearchChange: (query: string) => void;
  selectedSegmentId: number | null;
  onSelectSegment: (id: number) => void;
  onUpdateSegment: (id: number, updates: Partial<SubtitleSegment>) => void;
  onDeleteSegment: (id: number) => void;
  onAddSegment: () => void;
  onApplyShift: (offsetSeconds: number) => void;
  canUndo: boolean;
  canRedo: boolean;
  onUndo: () => void;
  onRedo: () => void;
  onDownloadSRT: () => void;
  onDownloadVTT: () => void;
  onCopyClipboard: () => Promise<boolean>;
  disabled?: boolean;
}

export const SubtitleEditor: React.FC<SubtitleEditorProps> = ({
  segments,
  filteredSegments,
  searchQuery,
  onSearchChange,
  selectedSegmentId,
  onSelectSegment,
  onUpdateSegment,
  onDeleteSegment,
  onAddSegment,
  onApplyShift,
  canUndo,
  canRedo,
  onUndo,
  onRedo,
  onDownloadSRT,
  onDownloadVTT,
  onCopyClipboard,
  disabled = false,
}) => {
  const [copied, setCopied] = useState<boolean>(false);

  const handleCopy = async () => {
    const success = await onCopyClipboard();
    if (success) {
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    }
  };

  return (
    <div className="glass-card glass-card-specular p-5 flex flex-col gap-4">
      {/* Top Header: Title, Search, and Export Buttons */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 pb-3 border-b border-border-glass">
        {/* Title and Segment Count */}
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-brand-indigo/20 border border-brand-indigo/30 flex items-center justify-center shrink-0">
            <Languages className="w-4 h-4 text-brand-indigo" />
          </div>
          <div>
            <h2 className="text-sm font-semibold tracking-wide text-content-white uppercase flex items-center gap-2">
              Subtitle Editor
            </h2>
            <p className="text-xs text-content-dim font-mono">
              {segments.length > 0
                ? `${filteredSegments.length} of ${segments.length} lines`
                : 'No subtitles loaded'}
            </p>
          </div>
        </div>

        {/* Search & Export Actions */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Live Search Input */}
          <div className="relative min-w-[200px] max-w-xs">
            <Search className="w-3.5 h-3.5 text-content-dim absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder="Search text or timecode..."
              className="w-full bg-surface-input border border-border-input rounded-xl pl-9 pr-8 py-1.5 text-xs text-content-white placeholder-content-dim focus:outline-none focus:border-brand-indigo font-sans"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => onSearchChange('')}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-content-dim hover:text-white"
                title="Clear search"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          <div className="w-[1px] h-5 bg-border-card hidden sm:block" />

          {/* Download SRT */}
          <button
            type="button"
            onClick={onDownloadSRT}
            disabled={segments.length === 0 || disabled}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-input hover:bg-surface-dropdown border border-border-input text-xs font-medium text-content-muted hover:text-white transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            title="Download SubRip (.srt) file"
          >
            <Download className="w-3.5 h-3.5 text-brand-cyan" />
            <span>.SRT</span>
          </button>

          {/* Download VTT */}
          <button
            type="button"
            onClick={onDownloadVTT}
            disabled={segments.length === 0 || disabled}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-input hover:bg-surface-dropdown border border-border-input text-xs font-medium text-content-muted hover:text-white transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            title="Download WebVTT (.vtt) file"
          >
            <Download className="w-3.5 h-3.5 text-brand-pink" />
            <span>.VTT</span>
          </button>

          {/* Copy to Clipboard */}
          <button
            type="button"
            onClick={handleCopy}
            disabled={segments.length === 0 || disabled}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium transition-all ${
              copied
                ? 'bg-brand-emerald-bg text-brand-emerald border-brand-emerald/40'
                : 'bg-surface-input hover:bg-surface-dropdown border-border-input text-content-muted hover:text-white disabled:opacity-40 disabled:cursor-not-allowed'
            }`}
            title="Copy all subtitles in SRT format to clipboard"
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-brand-emerald" />
                <span>Copied!</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5 text-content-muted" />
                <span>Copy</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Bulk Time Shift Controls */}
      <TimeShiftControls
        onApplyShift={onApplyShift}
        onAddSegment={onAddSegment}
        canUndo={canUndo}
        canRedo={canRedo}
        onUndo={onUndo}
        onRedo={onRedo}
        totalSegments={segments.length}
        disabled={disabled}
      />

      {/* Subtitles Table */}
      <div className="w-full overflow-x-auto rounded-xl border border-border-card/60 bg-surface-card/40 max-h-[460px] overflow-y-auto">
        <table className="w-full text-left border-collapse">
          <thead className="sticky top-0 z-10 bg-surface-header backdrop-blur-md border-b border-border-card text-[11px] font-semibold text-content-dim uppercase tracking-wider">
            <tr>
              <th className="px-3 py-2.5 text-center w-12 font-mono">#</th>
              <th className="px-2 py-2.5 text-center w-28 font-mono">Start Time</th>
              <th className="px-2 py-2.5 text-center w-28 font-mono">End Time</th>
              <th className="px-3 py-2.5 min-w-[200px]">Original Dialogue</th>
              <th className="px-3 py-2.5 min-w-[260px]">Thai Translation (Kanit)</th>
              <th className="px-2 py-2.5 text-center w-12">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredSegments.length > 0 ? (
              filteredSegments.map((seg) => (
                <SubtitleRow
                  key={seg.id}
                  segment={seg}
                  isSelected={selectedSegmentId === seg.id}
                  onSelect={() => onSelectSegment(seg.id)}
                  onUpdate={(updates) => onUpdateSegment(seg.id, updates)}
                  onDelete={() => onDeleteSegment(seg.id)}
                  disabled={disabled}
                />
              ))
            ) : (
              <tr>
                <td colSpan={6} className="py-12 text-center text-content-dim">
                  <div className="flex flex-col items-center justify-center">
                    <FileText className="w-8 h-8 text-content-dim/40 mb-2" />
                    <p className="text-xs font-medium">
                      {segments.length === 0
                        ? 'No subtitles loaded yet. Select a video and click "Transcribe & Translate", or click "Add Segment".'
                        : 'No segments matching search query.'}
                    </p>
                  </div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
