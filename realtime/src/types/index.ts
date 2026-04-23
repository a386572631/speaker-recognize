export interface TranscriptionSegment {
  text: string;
  speaker: string;
  start_time: number;
  end_time: number;
  similarity: number | null;
}

export interface TranscriptionResult {
  segments: TranscriptionSegment[];
  last_speaker: string;
}

export interface SpeakerColor {
  bg: string;
  text: string;
  border: string;
}