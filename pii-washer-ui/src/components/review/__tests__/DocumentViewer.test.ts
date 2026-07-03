import { describe, it, expect } from 'vitest';
import { buildSegments } from '../buildSegments';
import type { Detection, DetectionPosition } from '@/types/api';

// Minimal Detection — buildSegments only reads `id` and `positions`.
function det(id: string, positions: DetectionPosition[]): Detection {
  return {
    id,
    category: 'NAME',
    original_value: '',
    placeholder: '',
    status: 'pending',
    positions,
    confidence: 0.9,
    source: 'auto',
  };
}

describe('buildSegments', () => {
  it('returns the whole text as one plain segment when there are no detections', () => {
    expect(buildSegments('hello world', [])).toEqual([
      { type: 'plain', text: 'hello world' },
    ]);
  });

  it('splits a single detection into plain / highlight / plain', () => {
    // "hi John bye" — "John" at [3,7)
    const segs = buildSegments('hi John bye', [det('d1', [{ start: 3, end: 7 }])]);
    expect(segs.map((s) => [s.type, s.text])).toEqual([
      ['plain', 'hi '],
      ['highlight', 'John'],
      ['plain', ' bye'],
    ]);
  });

  it('marks only the first span of a repeated detection as isFirstOccurrence', () => {
    const d = det('d1', [
      { start: 0, end: 4 },
      { start: 9, end: 13 },
    ]);
    const segs = buildSegments('John and John', [d]);
    const highlights = segs.filter((s) => s.type === 'highlight');
    expect(highlights.map((h) => h.isFirstOccurrence)).toEqual([true, false]);
  });

  it('drops a range that overlaps one already emitted', () => {
    // [0,5) wins; [2,7) starts before the cursor (5) and is skipped
    const segs = buildSegments('abcdefgh', [
      det('d1', [{ start: 0, end: 5 }]),
      det('d2', [{ start: 2, end: 7 }]),
    ]);
    const highlights = segs.filter((s) => s.type === 'highlight');
    expect(highlights.map((h) => h.text)).toEqual(['abcde']);
  });

  it('emits no empty plain segment between adjacent ranges', () => {
    // [0,2) and [2,4) touch with no gap
    const segs = buildSegments('abcd', [
      det('d1', [{ start: 0, end: 2 }]),
      det('d2', [{ start: 2, end: 4 }]),
    ]);
    expect(segs.map((s) => [s.type, s.text])).toEqual([
      ['highlight', 'ab'],
      ['highlight', 'cd'],
    ]);
  });

  it('keeps the longer range when two start at the same position', () => {
    // tie at start 0 → longer [0,5) sorts first and wins; [0,3) is then skipped
    const segs = buildSegments('abcdefg', [
      det('short', [{ start: 0, end: 3 }]),
      det('long', [{ start: 0, end: 5 }]),
    ]);
    const highlights = segs.filter((s) => s.type === 'highlight');
    expect(highlights.map((h) => h.text)).toEqual(['abcde']);
    expect(highlights.map((h) => h.detection?.id)).toEqual(['long']);
  });
});
