import assert from 'node:assert/strict';
import test from 'node:test';
import {
  formatTimecode,
  parseTimecode,
  shiftSegments,
  serializeToSRT,
  serializeToVTT,
  parseSRT,
} from './timecode.ts';
import type { SubtitleSegment } from '../types/subtitle.ts';

test('formatTimecode handles zero and positive seconds', () => {
  assert.equal(formatTimecode(0), '00:00:00,000');
  assert.equal(formatTimecode(1.25), '00:00:01,250');
  assert.equal(formatTimecode(65.5), '00:01:05,500');
  assert.equal(formatTimecode(3661.123), '01:01:01,123');
  assert.equal(formatTimecode(1.25, '.'), '00:00:01.250');
});

test('formatTimecode clamps negative or NaN seconds safely', () => {
  assert.equal(formatTimecode(-5), '00:00:00,000');
  assert.equal(formatTimecode(NaN), '00:00:00,000');
});

test('parseTimecode correctly parses SRT and VTT formats', () => {
  assert.equal(parseTimecode('00:00:01,250'), 1.25);
  assert.equal(parseTimecode('00:01:05.500'), 65.5);
  assert.equal(parseTimecode('01:01:01,123'), 3661.123);
  assert.equal(parseTimecode('01:15,250'), 75.25);
});

test('parseTimecode returns null for invalid formats', () => {
  assert.equal(parseTimecode(''), null);
  assert.equal(parseTimecode('invalid'), null);
  assert.equal(parseTimecode('99:99'), null);
});

test('shiftSegments shifts timestamps and guarantees positive start and min duration', () => {
  const initial: SubtitleSegment[] = [
    {
      id: 1,
      start: 1.0,
      end: 3.0,
      start_str: '00:00:01,000',
      end_str: '00:00:03,000',
      text: 'Hello',
      thai_text: 'สวัสดี',
    },
    {
      id: 2,
      start: 4.0,
      end: 6.0,
      start_str: '00:00:04,000',
      end_str: '00:00:06,000',
      text: 'World',
      thai_text: 'ชาวโลก',
    },
  ];

  // Positive shift +0.5s
  const shiftedPos = shiftSegments(initial, 0.5);
  assert.equal(shiftedPos[0].start, 1.5);
  assert.equal(shiftedPos[0].end, 3.5);
  assert.equal(shiftedPos[0].start_str, '00:00:01,500');
  assert.equal(shiftedPos[0].end_str, '00:00:03,500');

  // Negative shift -2.0s (segment 1 clamped to 0 start, min 0.1s duration)
  const shiftedNeg = shiftSegments(initial, -2.0);
  assert.equal(shiftedNeg[0].start, 0);
  assert.equal(shiftedNeg[0].end, 1.0);
  assert.equal(shiftedNeg[0].start_str, '00:00:00,000');
  assert.equal(shiftedNeg[0].end_str, '00:00:01,000');
});

test('serializeToSRT and serializeToVTT generate valid formats', () => {
  const segments: SubtitleSegment[] = [
    {
      id: 1,
      start: 1.0,
      end: 2.5,
      start_str: '00:00:01,000',
      end_str: '00:00:02,500',
      text: 'おはよう',
      thai_text: 'อรุณสวัสดิ์',
    },
  ];

  const srt = serializeToSRT(segments);
  assert.ok(srt.includes('1\n00:00:01,000 --> 00:00:02,500\nอรุณสวัสดิ์'));

  const vtt = serializeToVTT(segments);
  assert.ok(vtt.startsWith('WEBVTT'));
  assert.ok(vtt.includes('1\n00:00:01.000 --> 00:00:02.500\nอรุณสวัสดิ์'));
});

test('parseSRT parses serialized SRT text back into segments', () => {
  const rawSrt = `1
00:00:01,250 --> 00:00:03,500
こんにちは

2
00:00:04,000 --> 00:00:06,200
ありがとう
`;

  const parsed = parseSRT(rawSrt);
  assert.equal(parsed.length, 2);
  assert.equal(parsed[0].id, 1);
  assert.equal(parsed[0].start, 1.25);
  assert.equal(parsed[0].end, 3.5);
  assert.equal(parsed[0].text, 'こんにちは');
  assert.equal(parsed[1].id, 2);
  assert.equal(parsed[1].start, 4.0);
  assert.equal(parsed[1].end, 6.2);
  assert.equal(parsed[1].text, 'ありがとう');
});
