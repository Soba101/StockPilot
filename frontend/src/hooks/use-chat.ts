import { useMutation } from '@tanstack/react-query';
import { chatApi } from '@/lib/api';

export interface ChatQueryResponse {
  title: string;
  answer_summary: string;
  data?: { columns: { name: string; type: string }[]; rows: any[] } | undefined;
  query_explainer?: { definition?: string; sql?: string | null; sources?: string[] } | {};
  confidence: { level: 'high' | 'medium' | 'low' };
  source: 'rules' | 'llm';
}

export function useChatQuery() {
  return useMutation<ChatQueryResponse, Error, { prompt: string }>({
    mutationFn: (vars) => chatApi.query({ prompt: vars.prompt }),
  });
}
