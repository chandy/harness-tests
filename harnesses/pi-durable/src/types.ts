export type AgentResult = {
  harness: string;
  task_id: string;
  passed: boolean;
  steps: number;
  wall_time_ms: number;
  tokens_in: number | null;
  tokens_out: number | null;
  cost_usd: number | null;
  model: string;
  message: string;
  error: string | null;
  tool_calls: Array<{
    tool: string;
    args: Record<string, unknown>;
    result_preview: string;
  }>;
};
