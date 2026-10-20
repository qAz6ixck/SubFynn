export interface SubtitleSegment {
  id: number;
  start: number;       // Seconds (e.g. 1.250)
  end: number;         // Seconds (e.g. 3.420)
  start_str: string;   // "00:00:01,250"
  end_str: string;     // "00:00:03,420"
  text: string;        // Source text (Japanese/English)
  thai_text: string;   // Translated Thai text
}

export interface SubtitleEditorState {
  segments: SubtitleSegment[];
  searchQuery: string;
  selectedSegmentId: number | null;
  history: SubtitleSegment[][];
  historyIndex: number;
}

export type WhisperModel = 'large-v3' | 'large-v2' | 'medium' | 'small' | 'base';

export type GeminiModel =
  | 'gemini-3.5-live-translate-preview'
  | 'cloud-translation-llm'
  | 'gemini-2.5-flash';

export type TranslationStyle =
  | 'jav_dirty'
  | 'jav'
  | 'jav_sweet'
  | 'general'
  | 'anime';

export type AudioLanguage = 'ja' | 'auto' | 'en' | 'zh' | 'ko' | 'th';

export interface ModelConfig {
  whisperModel: WhisperModel;
  geminiModel: GeminiModel;
  translationStyle: TranslationStyle;
  audioLanguage: AudioLanguage;
  geminiApiKey: string;
}

export interface PipelineProgress {
  percent: number;
  stage: string;
  message: string;
  task_id?: number;
}

export interface PipelineResult {
  segments: SubtitleSegment[];
  srt_path?: string;
  vtt_path?: string;
  srt_content?: string;
  vtt_content?: string;
  output_video_path?: string;
}

export interface HardwareStatus {
  cudaAvailable: boolean;
  deviceString: string;
}
