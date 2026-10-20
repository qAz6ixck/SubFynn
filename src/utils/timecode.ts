import type { SubtitleSegment } from '../types/subtitle.ts';

/**
 * Formats a number of seconds into an SRT or VTT timecode string.
 * e.g., 75.25 with ',' -> "00:01:15,250"
 */
export function formatTimecode(seconds: number, delimiter: ',' | '.' = ','): string {
  const safeSec = Math.max(0, isNaN(seconds) ? 0 : seconds);
  const hrs = Math.floor(safeSec / 3600);
  const mins = Math.floor((safeSec % 3600) / 60);
  const secs = Math.floor(safeSec % 60);
  const millis = Math.min(999, Math.round((safeSec - Math.floor(safeSec)) * 1000));

  const pad = (n: number, z = 2) => String(n).padStart(z, '0');
  return `${pad(hrs)}:${pad(mins)}:${pad(secs)}${delimiter}${pad(millis, 3)}`;
}

/**
 * Parses an SRT or VTT timecode string into float seconds.
 * Accepts "00:01:15,250" or "00:01:15.250" or "01:15.250".
 * Returns null if the format is invalid.
 */
export function parseTimecode(tc: string): number | null {
  if (!tc || typeof tc !== 'string') return null;
  const cleaned = tc.trim();

  // Full format: HH:MM:SS,mmm or HH:MM:SS.mmm
  const fullMatch = cleaned.match(/^(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})$/);
  if (fullMatch) {
    const [, h, m, s, msRaw] = fullMatch;
    const ms = msRaw.padEnd(3, '0').slice(0, 3);
    return Number(h) * 3600 + Number(m) * 60 + Number(s) + Number(ms) / 1000;
  }

  // Short format: MM:SS,mmm or MM:SS.mmm
  const shortMatch = cleaned.match(/^(\d{1,2}):(\d{2})[,.](\d{1,3})$/);
  if (shortMatch) {
    const [, m, s, msRaw] = shortMatch;
    const ms = msRaw.padEnd(3, '0').slice(0, 3);
    return Number(m) * 60 + Number(s) + Number(ms) / 1000;
  }

  return null;
}

/**
 * Shifts all segments (or segments starting from fromId) by offsetSeconds.
 */
export function shiftSegments(
  segments: SubtitleSegment[],
  offsetSeconds: number,
  fromId: number = 1
): SubtitleSegment[] {
  return segments.map((seg) => {
    if (seg.id < fromId) return seg;
    const newStart = Math.max(0, Math.round((seg.start + offsetSeconds) * 1000) / 1000);
    const newEnd = Math.max(newStart + 0.1, Math.round((seg.end + offsetSeconds) * 1000) / 1000);
    return {
      ...seg,
      start: newStart,
      end: newEnd,
      start_str: formatTimecode(newStart, ','),
      end_str: formatTimecode(newEnd, ','),
    };
  });
}

/**
 * Serializes segments to standard SubRip (.srt) format.
 */
export function serializeToSRT(segments: SubtitleSegment[]): string {
  if (!segments || segments.length === 0) return '';
  return segments
    .map((s, i) => {
      const textContent = (s.thai_text || s.text || '').trim();
      return `${i + 1}\n${formatTimecode(s.start, ',')} --> ${formatTimecode(s.end, ',')}\n${textContent}\n`;
    })
    .join('\n');
}

/**
 * Serializes segments to standard WebVTT (.vtt) format.
 */
export function serializeToVTT(segments: SubtitleSegment[]): string {
  const lines = ['WEBVTT\n'];
  segments.forEach((s, i) => {
    const textContent = (s.thai_text || s.text || '').trim();
    lines.push(
      `${i + 1}\n${formatTimecode(s.start, '.')} --> ${formatTimecode(s.end, '.')}\n${textContent}\n`
    );
  });
  return lines.join('\n');
}

/**
 * Parses raw SRT string into SubtitleSegment array.
 */
export function parseSRT(srtContent: string): SubtitleSegment[] {
  const segments: SubtitleSegment[] = [];
  if (!srtContent) return segments;

  const blocks = srtContent.replace(/\r\n/g, '\n').split(/\n\s*\n/);
  let idCounter = 1;

  for (const block of blocks) {
    const lines = block.trim().split('\n');
    if (lines.length < 2) continue;

    let timeLineIdx = 0;
    if (/^\d+$/.test(lines[0].trim())) {
      timeLineIdx = 1;
    }

    const timeLine = lines[timeLineIdx];
    if (!timeLine || !timeLine.includes('-->')) continue;

    const [startStr, endStr] = timeLine.split('-->').map((s) => s.trim());
    const startSec = parseTimecode(startStr);
    const endSec = parseTimecode(endStr);

    if (startSec === null || endSec === null) continue;

    const textLines = lines.slice(timeLineIdx + 1).join('\n');

    segments.push({
      id: idCounter++,
      start: startSec,
      end: endSec,
      start_str: formatTimecode(startSec, ','),
      end_str: formatTimecode(endSec, ','),
      text: textLines,
      thai_text: textLines,
    });
  }

  return segments;
}

/**
 * Triggers a browser download of text data as a file.
 */
export function triggerDownload(filename: string, content: string, mimeType = 'text/plain;charset=utf-8'): void {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * Copies text to the system clipboard.
 */
export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.opacity = '0';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    const success = document.execCommand('copy');
    document.body.removeChild(textArea);
    return success;
  } catch (err) {
    console.error('Clipboard copy failed:', err);
    return false;
  }
}
