import { Injectable } from '@angular/core';

type SpeechRecognitionConstructor = new () => SpeechRecognitionLike;

interface SpeechRecognitionEventLike extends Event {
  results: ArrayLike<{
    isFinal: boolean;
    0: {
      transcript: string;
      confidence: number;
    };
  }>;
}

interface SpeechRecognitionErrorEventLike extends Event {
  error: string;
  message?: string;
}

interface SpeechRecognitionLike {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  maxAlternatives: number;
  onstart: (() => void) | null;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEventLike) => void) | null;
  onend: (() => void) | null;
  start(): void;
  stop(): void;
  abort(): void;
}

interface VoiceCallbacks {
  onStart?: () => void;
  onResult?: (transcript: string, isFinal: boolean) => void;
  onError?: (message: string) => void;
  onEnd?: () => void;
}

interface VoiceWindow extends Window {
  SpeechRecognition?: SpeechRecognitionConstructor;
  webkitSpeechRecognition?: SpeechRecognitionConstructor;
}

@Injectable({
  providedIn: 'root'
})
export class VoiceService {
  private recognition: SpeechRecognitionLike | null = null;
  private listening = false;
  private muted = false;

  isSpeechRecognitionSupported(): boolean {
    const voiceWindow = window as VoiceWindow;

    return Boolean(
      voiceWindow.SpeechRecognition ||
      voiceWindow.webkitSpeechRecognition
    );
  }

  isSpeechSynthesisSupported(): boolean {
    return (
      'speechSynthesis' in window &&
      'SpeechSynthesisUtterance' in window
    );
  }

  isListening(): boolean {
    return this.listening;
  }

  isMuted(): boolean {
    return this.muted;
  }

  setMuted(muted: boolean): void {
    this.muted = muted;

    if (muted) {
      this.stopSpeaking();
    }
  }

  startListening(
    callbacks: VoiceCallbacks,
    language = 'en-GB'
  ): void {
    if (!this.isSpeechRecognitionSupported()) {
      callbacks.onError?.(
        'Voice input is not supported in this browser. Please use Google Chrome or Microsoft Edge.'
      );
      return;
    }

    this.stopListening();
    this.stopSpeaking();

    const voiceWindow = window as VoiceWindow;
    const Recognition =
      voiceWindow.SpeechRecognition ||
      voiceWindow.webkitSpeechRecognition;

    if (!Recognition) {
      callbacks.onError?.(
        'Speech recognition could not be started.'
      );
      return;
    }

    const recognition = new Recognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = language;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
      this.listening = true;
      callbacks.onStart?.();
    };

    recognition.onresult = event => {
      let transcript = '';
      let isFinal = false;

      for (let index = 0; index < event.results.length; index += 1) {
        const result = event.results[index];
        transcript += result[0]?.transcript ?? '';

        if (result.isFinal) {
          isFinal = true;
        }
      }

      callbacks.onResult?.(
        transcript.trim(),
        isFinal
      );
    };

    recognition.onerror = event => {
      this.listening = false;
      callbacks.onError?.(
        this.getFriendlyRecognitionError(event.error)
      );
    };

    recognition.onend = () => {
      this.listening = false;
      callbacks.onEnd?.();
    };

    this.recognition = recognition;

    try {
      recognition.start();
    } catch (error) {
      console.error('Speech recognition start error:', error);
      this.listening = false;
      callbacks.onError?.(
        'The microphone could not be started. Please try again.'
      );
    }
  }

  stopListening(): void {
    if (!this.recognition) {
      this.listening = false;
      return;
    }

    try {
      this.recognition.stop();
    } catch {
      // Recognition may already be stopped.
    }

    this.listening = false;
    this.recognition = null;
  }

  speak(
    text: string,
    onStart?: () => void,
    onEnd?: () => void
  ): void {
    if (
      this.muted ||
      !text.trim() ||
      !this.isSpeechSynthesisSupported()
    ) {
      onEnd?.();
      return;
    }

    this.stopSpeaking();

    const utterance = new SpeechSynthesisUtterance(
      this.cleanTextForSpeech(text)
    );

    utterance.lang = 'en-GB';
    utterance.rate = 1;
    utterance.pitch = 1;
    utterance.volume = 1;

    utterance.onstart = () => onStart?.();
    utterance.onend = () => onEnd?.();
    utterance.onerror = () => onEnd?.();

    window.speechSynthesis.speak(utterance);
  }

  stopSpeaking(): void {
    if (this.isSpeechSynthesisSupported()) {
      window.speechSynthesis.cancel();
    }
  }

  destroy(): void {
    if (this.recognition) {
      try {
        this.recognition.abort();
      } catch {
        // Recognition may already be inactive.
      }
    }

    this.recognition = null;
    this.listening = false;
    this.stopSpeaking();
  }

  private cleanTextForSpeech(text: string): string {
    return text
      .replace(/https?:\/\/\S+/gi, '')
      .replace(/[*_`#>]/g, '')
      .replace(/\s+/g, ' ')
      .trim();
  }

  private getFriendlyRecognitionError(error: string): string {
    switch (error) {
      case 'not-allowed':
      case 'service-not-allowed':
        return 'Microphone permission was denied. Allow microphone access in your browser settings and try again.';
      case 'no-speech':
        return 'No speech was detected. Please click the microphone and speak again.';
      case 'audio-capture':
        return 'No microphone was found. Check that your microphone is connected and enabled.';
      case 'network':
        return 'Voice recognition could not connect. Check your internet connection and try again.';
      case 'aborted':
        return '';
      default:
        return 'Voice recognition stopped unexpectedly. Please try again.';
    }
  }
}
