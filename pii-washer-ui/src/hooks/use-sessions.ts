import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getSession,
  getSessionStatus,
  resetSession,
} from '@/api/sessions';
import { useSessionStore } from '@/store/session-store';

export function useSession(sessionId: string | null) {
  return useQuery({
    queryKey: ['session', sessionId],
    queryFn: () => getSession(sessionId!),
    enabled: !!sessionId,
  });
}

export function useSessionStatus(sessionId: string | null) {
  return useQuery({
    queryKey: ['sessionStatus', sessionId],
    queryFn: () => getSessionStatus(sessionId!),
    enabled: !!sessionId,
  });
}

export function useResetSession() {
  const queryClient = useQueryClient();
  const resetStore = useSessionStore((s) => s.resetSession);

  return useMutation({
    mutationFn: resetSession,
    onSuccess: () => {
      // Targeted invalidation — only session-scoped queries. Preserves
      // unrelated caches.
      queryClient.invalidateQueries({ queryKey: ['session'] });
      queryClient.invalidateQueries({ queryKey: ['sessionStatus'] });
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
      resetStore();
    },
  });
}
