export interface ChildProfile {
  child_id: string;
  nickname: string;
  age: number;
}

export interface HealthResponse {
  status: string;
  environment: string;
  model_provider: string;
  model?: string;
  persistence: string;
}

export interface TurnRequest {
  message: string;
  child: ChildProfile;
  turn_id: string;
}

export interface SafetyResult {
  risk_level: string;
  matched_signals: string[];
  reason: string;
}

export interface EmotionAnalysis {
  event_summary: string;
  primary_emotion: string;
  emotion_intensity: number;
  emotion_clues: string[];
  known_facts: string[];
  missing_information: string[];
  confidence: number;
}

export interface StoryPage {
  page_number: number;
  text: string;
  illustration_prompt: string;
}

export interface StoryBook {
  title: string;
  emotional_goal: string;
  pages: StoryPage[];
}

export interface ParentGuidance {
  observation: string;
  suggested_response: string;
  shared_reading_question: string;
  next_action: string;
  disclaimer: string;
}

export interface ToolTraceItem {
  step: number;
  node: string;
  summary: string;
}

export interface MemoryCandidate {
  summary: string;
  category: string;
  reason: string;
  requires_guardian_confirmation: boolean;
}

export interface ConfirmedMemory {
  memory_id: string;
  child_id: string;
  summary: string;
  category: string;
  created_at: string;
}

export interface TurnResponse {
  conversation_id: string;
  action: string;
  child_message: string;
  safety: SafetyResult;
  analysis?: EmotionAnalysis;
  story?: StoryBook;
  parent_guidance?: ParentGuidance;
  memory_candidate?: MemoryCandidate;
  tool_trace: ToolTraceItem[];
  model_provider: string;
}
