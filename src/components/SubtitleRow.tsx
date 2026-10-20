import React, { useState, useEffect } from 'react';
import { Trash2 } from 'lucide-react';
import { SubtitleSegment } from '../types/subtitle';
import { parseTimecode, formatTimecode } from '../utils/timecode';

interface SubtitleRowProps {
  segment: SubtitleSegment;
  isSelected: boolean;
  onSelect: () => void;
  onUpdate: (updates: Partial<SubtitleSegment>) => void;
  onDelete: () => void;
  disabled?: boolean;
}

export const SubtitleRow: React.FC<SubtitleRowProps> = ({
  segment,
  isSelected,
  onSelect,
  onUpdate,
  onDelete,
  disabled = false,
}) => {
  const [startStr, setStartStr] = useState<string>(segment.start_str);
  const [endStr, setEndStr] = useState<string>(segment.end_str);
  const [sourceText, setSourceText] = useState<string>(segment.text);
  const [thaiText, setThaiText] = useState<string>(segment.thai_text);
  const [timeError, setTimeError] = useState<boolean>(false);

  // Sync internal state when prop changes externally (e.g. time shift, undo)
  useEffect(() => {
    setStartStr(segment.start_str);
    setEndStr(segment.end_str);
    setSourceText(segment.text);
    setThaiText(segment.thai_text);
    setTimeError(false);
  }, [segment.start_str, segment.end_str, segment.text, segment.thai_text]);

  // Handle start time blur & commit
  const handleStartBlur = () => {
    const sec = parseTimecode(startStr);
    if (sec === null) {
      setTimeError(true);
      setStartStr(segment.start_str);
      setTimeout(() => setTimeError(false), 800);
      return;
    }
    const formatted = formatTimecode(sec, ',');
    setStartStr(formatted);
    onUpdate({ start: sec, start_str: formatted });
  };

  // Handle end time blur & commit
  const handleEndBlur = () => {
    const sec = parseTimecode(endStr);
    if (sec === null) {
      setTimeError(true);
      setEndStr(segment.end_str);
      setTimeout(() => setTimeError(false), 800);
      return;
    }
    const formatted = formatTimecode(sec, ',');
    setEndStr(formatted);
    onUpdate({ end: sec, end_str: formatted });
  };

  // Handle text blur & commit
  const handleSourceBlur = () => {
    if (sourceText !== segment.text) {
      onUpdate({ text: sourceText });
    }
  };

  const handleThaiBlur = () => {
    if (thaiText !== segment.thai_text) {
      onUpdate({ thai_text: thaiText });
    }
  };

  return (
    <tr
      onClick={onSelect}
      className={`border-b border-border-card/60 transition-colors group ${
        isSelected
          ? 'bg-brand-indigo/15'
          : 'hover:bg-surface-card-hover bg-transparent'
      }`}
    >
      {/* 1. Sequence ID */}
      <td className="px-3 py-2 text-center text-xs font-mono text-content-dim whitespace-nowrap w-12">
        <span className="px-2 py-0.5 rounded bg-surface-input border border-border-card text-[11px]">
          {segment.id}
        </span>
      </td>

      {/* 2. Start Timecode */}
      <td className="px-2 py-2 whitespace-nowrap w-28">
        <input
          type="text"
          value={startStr}
          onChange={(e) => setStartStr(e.target.value)}
          onBlur={handleStartBlur}
          disabled={disabled}
          className={`w-full bg-surface-input/70 border rounded-lg px-2 py-1 text-xs font-mono text-content-white focus:outline-none focus:border-brand-indigo focus:bg-surface-input transition-colors text-center ${
            timeError ? 'border-brand-rose' : 'border-border-input'
          }`}
          title="Start timecode (00:00:00,000)"
        />
      </td>

      {/* 3. End Timecode */}
      <td className="px-2 py-2 whitespace-nowrap w-28">
        <input
          type="text"
          value={endStr}
          onChange={(e) => setEndStr(e.target.value)}
          onBlur={handleEndBlur}
          disabled={disabled}
          className={`w-full bg-surface-input/70 border rounded-lg px-2 py-1 text-xs font-mono text-content-white focus:outline-none focus:border-brand-indigo focus:bg-surface-input transition-colors text-center ${
            timeError ? 'border-brand-rose' : 'border-border-input'
          }`}
          title="End timecode (00:00:00,000)"
        />
      </td>

      {/* 4. Original Source Text */}
      <td className="px-3 py-2 min-w-[200px]">
        <textarea
          rows={1}
          value={sourceText}
          onChange={(e) => setSourceText(e.target.value)}
          onBlur={handleSourceBlur}
          disabled={disabled}
          placeholder="Source text..."
          className="w-full bg-transparent border-0 rounded p-1 text-xs text-content-muted focus:bg-surface-input/80 focus:ring-1 focus:ring-brand-indigo/50 focus:outline-none resize-none transition-colors"
        />
      </td>

      {/* 5. Translated Thai Text (Kanit font, bold high contrast) */}
      <td className="px-3 py-2 min-w-[260px]">
        <textarea
          rows={1}
          value={thaiText}
          onChange={(e) => setThaiText(e.target.value)}
          onBlur={handleThaiBlur}
          disabled={disabled}
          placeholder="ข้อความซับไตเติลภาษาไทย..."
          className="w-full bg-transparent border-0 rounded p-1 text-sm font-thai text-content-white focus:bg-surface-input/80 focus:ring-1 focus:ring-brand-indigo focus:outline-none resize-none transition-colors font-medium leading-relaxed"
        />
      </td>

      {/* 6. Delete Action */}
      <td className="px-2 py-2 text-center whitespace-nowrap w-12">
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
          disabled={disabled}
          className="p-1.5 rounded-lg text-content-dim hover:text-brand-rose hover:bg-brand-rose/15 transition-colors opacity-0 group-hover:opacity-100 focus:opacity-100"
          title="Delete segment"
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </td>
    </tr>
  );
};
