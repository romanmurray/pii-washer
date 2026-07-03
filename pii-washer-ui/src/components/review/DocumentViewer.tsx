import { ScrollArea } from '@/components/ui/scroll-area';
import { HighlightSpan } from './HighlightSpan';
import { buildSegments } from './buildSegments';
import type { Detection } from '@/types/api';

interface DocumentViewerProps {
  originalText: string;
  detections: Detection[];
  focusedDetectionId: string | null;
  onDetectionClick: (detectionId: string) => void;
  onDocumentClick: () => void;
}

export function DocumentViewer({
  originalText,
  detections,
  focusedDetectionId,
  onDetectionClick,
  onDocumentClick,
}: DocumentViewerProps) {
  const segments = buildSegments(originalText, detections);

  return (
    <ScrollArea className="h-full">
      <div
        className="p-6 text-sm leading-relaxed select-text"
        style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit' }}
        onClick={() => {
          const sel = window.getSelection();
          if (sel && sel.toString().length > 0) return;
          onDocumentClick();
        }}
      >
        {segments.map((seg, i) => {
          if (seg.type === 'plain') {
            return <span key={i}>{seg.text}</span>;
          }
          return (
            <HighlightSpan
              key={i}
              detection={seg.detection!}
              text={seg.text}
              isFocused={focusedDetectionId === seg.detection!.id}
              isFirstOccurrence={seg.isFirstOccurrence!}
              onClick={onDetectionClick}
            />
          );
        })}
      </div>
    </ScrollArea>
  );
}
