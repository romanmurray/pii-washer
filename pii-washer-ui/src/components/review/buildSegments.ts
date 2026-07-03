import type { Detection } from '@/types/api';

export interface Segment {
  type: 'plain' | 'highlight';
  text: string;
  detection?: Detection;
  /** True only for the first rendered span of a given detection */
  isFirstOccurrence?: boolean;
}

/**
 * Split `text` into plain and highlighted segments for the document viewer.
 * Handles the bug-prone cases: overlapping ranges (later one dropped),
 * adjacent ranges (no empty gap), and repeated matches of the same detection
 * (only the first span is flagged isFirstOccurrence).
 */
export function buildSegments(text: string, detections: Detection[]): Segment[] {
  const ranges: { start: number; end: number; detection: Detection }[] = [];
  for (const det of detections) {
    for (const pos of det.positions) {
      ranges.push({ start: pos.start, end: pos.end, detection: det });
    }
  }

  // Sort by start; on tie, longer range first
  ranges.sort((a, b) => a.start - b.start || b.end - a.end);

  const segments: Segment[] = [];
  const seenDetections = new Set<string>();
  let cursor = 0;

  for (const range of ranges) {
    // Skip overlapping ranges
    if (range.start < cursor) continue;

    if (range.start > cursor) {
      segments.push({ type: 'plain', text: text.slice(cursor, range.start) });
    }

    const isFirstOccurrence = !seenDetections.has(range.detection.id);
    seenDetections.add(range.detection.id);

    segments.push({
      type: 'highlight',
      text: text.slice(range.start, range.end),
      detection: range.detection,
      isFirstOccurrence,
    });

    cursor = range.end;
  }

  if (cursor < text.length) {
    segments.push({ type: 'plain', text: text.slice(cursor) });
  }

  return segments;
}
