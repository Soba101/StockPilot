import { useMutation } from '@tanstack/react-query';
import { chatApi } from '@/lib/api';

export interface ChatQueryResponse {
  intent: string | null;
  title: string;
  answer_summary: string;
  data: { columns: { name: string; type: string }[]; rows: any[] };
  query_explainer: { definition: string; sql?: string | null; sources: string[] };
  freshness: { generated_at: string; data_fresh_at?: string | null; max_lag_seconds?: number | null };
  confidence: { level: 'high' | 'medium' | 'low'; reasons: string[] };
  warnings: string[];
  source: 'rules' | 'llm';
}

export function useChatQuery() {
  return useMutation<ChatQueryResponse, Error, { prompt: string } | { intent: string; params?: Record<string, any> }>({
    mutationFn: (vars) => {
      if ('prompt' in vars) return chatApi.query({ prompt: vars.prompt });
      return chatApi.query({ prompt: '', intent: vars.intent, params: vars.params });
    },
  });
}
