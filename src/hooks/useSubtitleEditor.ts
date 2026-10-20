import { useState, useCallback, useMemo } from 'react';
import { SubtitleSegment } from '../types/subtitle';
import {
  shiftSegments,
  serializeToSRT,
  serializeToVTT,
  triggerDownload,
  copyToClipboard,
  formatTimecode,
  parseTimecode,
} from '../utils/timecode';

const MAX_HISTORY = 30;

export function useSubtitleEditor(initialSegments: SubtitleSegment[] = []) {
  const [segments, setSegmentsState] = useState<SubtitleSegment[]>(initialSegments);
  const [history, setHistory] = useState<SubtitleSegment[][]>([initialSegments]);
  const [historyIndex, setHistoryIndex] = useState<number>(0);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedSegmentId, setSelectedSegmentId] = useState<number | null>(null);

  // Push new state to undo/redo history
  const pushHistory = useCallback(
    (newSegments: SubtitleSegment[]) => {
      setSegmentsState(newSegments);
      setHistory((prev) => {
        const sliced = prev.slice(0, historyIndex + 1);
        const next = [...sliced, newSegments];
        if (next.length > MAX_HISTORY) {
          return next.slice(next.length - MAX_HISTORY);
        }
        return next;
      });
      setHistoryIndex((prev) => Math.min(prev + 1, MAX_HISTORY - 1));
    },
    [historyIndex]
  );

  // Replace all segments (e.g. from pipeline finish)
  const setSegments = useCallback((newSegments: SubtitleSegment[]) => {
    setSegmentsState(newSegments);
    setHistory([newSegments]);
    setHistoryIndex(0);
    setSelectedSegmentId(null);
  }, []);

  // Update a single segment
  const updateSegment = useCallback(
    (id: number, updates: Partial<SubtitleSegment>) => {
      const next = segments.map((seg) => {
        if (seg.id !== id) return seg;
        const merged = { ...seg, ...updates };

        // If start was updated as number, re-format start_str
        if (updates.start !== undefined && updates.start_str === undefined) {
          merged.start_str = formatTimecode(updates.start, ',');
        }
        // If end was updated as number, re-format end_str
        if (updates.end !== undefined && updates.end_str === undefined) {
          merged.end_str = formatTimecode(updates.end, ',');
        }
        // If start_str was updated as string, re-parse start
        if (updates.start_str !== undefined && updates.start === undefined) {
          const parsed = parseTimecode(updates.start_str);
          if (parsed !== null) merged.start = parsed;
        }
        // If end_str was updated as string, re-parse end
        if (updates.end_str !== undefined && updates.end === undefined) {
          const parsed = parseTimecode(updates.end_str);
          if (parsed !== null) merged.end = parsed;
        }

        return merged;
      });
      pushHistory(next);
    },
    [segments, pushHistory]
  );

  // Delete a segment
  const deleteSegment = useCallback(
    (id: number) => {
      const filtered = segments.filter((s) => s.id !== id);
      // Re-index remaining segments
      const reindexed = filtered.map((s, index) => ({
        ...s,
        id: index + 1,
      }));
      pushHistory(reindexed);
    },
    [segments, pushHistory]
  );

  // Add a new segment
  const addSegment = useCallback(
    (afterId?: number) => {
      let insertIndex = segments.length;
      let startSec = 0;
      let endSec = 2.0;

      if (afterId !== undefined) {
        const foundIdx = segments.findIndex((s) => s.id === afterId);
        if (foundIdx !== -1) {
          insertIndex = foundIdx + 1;
          startSec = segments[foundIdx].end + 0.1;
          endSec = startSec + 2.0;
        }
      } else if (segments.length > 0) {
        const last = segments[segments.length - 1];
        startSec = last.end + 0.1;
        endSec = startSec + 2.0;
      }

      const newSeg: SubtitleSegment = {
        id: 0, // Will be reindexed
        start: startSec,
        end: endSec,
        start_str: formatTimecode(startSec, ','),
        end_str: formatTimecode(endSec, ','),
        text: '',
        thai_text: '',
      };

      const copy = [...segments];
      copy.splice(insertIndex, 0, newSeg);
      const reindexed = copy.map((s, idx) => ({ ...s, id: idx + 1 }));
      pushHistory(reindexed);
      setSelectedSegmentId(insertIndex + 1);
    },
    [segments, pushHistory]
  );

  // Bulk shift timestamps
  const applyTimeShift = useCallback(
    (offsetSeconds: number, fromId: number = 1) => {
      if (offsetSeconds === 0 || segments.length === 0) return;
      const shifted = shiftSegments(segments, offsetSeconds, fromId);
      pushHistory(shifted);
    },
    [segments, pushHistory]
  );

  // Undo / Redo
  const canUndo = historyIndex > 0;
  const canRedo = historyIndex < history.length - 1;

  const undo = useCallback(() => {
    if (!canUndo) return;
    const newIdx = historyIndex - 1;
    setHistoryIndex(newIdx);
    setSegmentsState(history[newIdx]);
  }, [canUndo, historyIndex, history]);

  const redo = useCallback(() => {
    if (!canRedo) return;
    const newIdx = historyIndex + 1;
    setHistoryIndex(newIdx);
    setSegmentsState(history[newIdx]);
  }, [canRedo, historyIndex, history]);

  // Filtered segments matching search query
  const filteredSegments = useMemo(() => {
    if (!searchQuery.trim()) return segments;
    const q = searchQuery.toLowerCase().trim();
    return segments.filter((s) => {
      return (
        s.text.toLowerCase().includes(q) ||
        s.thai_text.toLowerCase().includes(q) ||
        s.start_str.includes(q) ||
        s.end_str.includes(q) ||
        String(s.id) === q
      );
    });
  }, [segments, searchQuery]);

  // SRT / VTT export helpers
  const exportSRT = useCallback(() => serializeToSRT(segments), [segments]);
  const exportVTT = useCallback(() => serializeToVTT(segments), [segments]);

  const downloadSRT = useCallback(
    (filename = 'subtitles.srt') => {
      const content = serializeToSRT(segments);
      triggerDownload(filename, content, 'text/plain;charset=utf-8');
    },
    [segments]
  );

  const downloadVTT = useCallback(
    (filename = 'subtitles.vtt') => {
      const content = serializeToVTT(segments);
      triggerDownload(filename, content, 'text/vtt;charset=utf-8');
    },
    [segments]
  );

  const copySRTToClipboard = useCallback(async (): Promise<boolean> => {
    const content = serializeToSRT(segments);
    return await copyToClipboard(content);
  }, [segments]);

  return {
    segments,
    filteredSegments,
    searchQuery,
    setSearchQuery,
    selectedSegmentId,
    setSelectedSegmentId,
    setSegments,
    updateSegment,
    deleteSegment,
    addSegment,
    applyTimeShift,
    canUndo,
    canRedo,
    undo,
    redo,
    exportSRT,
    exportVTT,
    downloadSRT,
    downloadVTT,
    copySRTToClipboard,
  };
}
