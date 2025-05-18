export interface Message {
  id: string;
  content: string;
  role: MessageRole;
  timestamp: string;
  repository_id?: string;
  metadata?: MessageMetadata;
}

export enum MessageRole {
  USER = "user",
  ASSISTANT = "assistant",
  SYSTEM = "system"
}

export interface MessageMetadata {
  citations?: Citation[];
  tokens_used?: number;
  processing_time?: number;
  model?: string;
}

export interface Citation {
  file_path: string;
  snippet: string;
  start_line: number;
  end_line: number;
  relevance_score?: number;
}

export interface Conversation {
  id: string;
  title: string;
  repository_id: string;
  messages: Message[];
  created_at: string;
  updated_at: string;
}

export interface ChatRequest {
  repository_id: string;
  message: string;
  conversation_id?: string;
}

export interface ChatResponse {
  message: Message;
  conversation_id: string;
}

export interface ConversationsResponse {
  conversations: Conversation[];
}

export interface ConversationResponse {
  conversation: Conversation;
}

export interface ExampleQuestion {
  text: string;
  category?: string;
}
