import {
  ChangeDetectorRef,
  Component,
  ElementRef,
  OnDestroy,
  ViewChild,
  inject,
  signal
} from '@angular/core';

import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { RouterLink } from '@angular/router';
import { VoiceService } from '../services/voice.service';


interface ChatMessage {
  id: string;
  sender: 'customer' | 'assistant';
  message: string;
  createdAt: Date;
}


interface ChatRequest {
  message: string;
  conversation_id: string;
  business_id: string;
}


interface ChatResponse {
  reply: string;
  conversation_id: string;
  intent?: string;
  booking_ready?: boolean;
  appointment_created?: boolean;
  appointment_id?: string | null;
}


@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterLink
  ],
  templateUrl: './chat.html',
  styleUrl: './chat.css'
})
export class ChatComponent implements OnDestroy {
  private readonly http = inject(HttpClient);
  private readonly voiceService = inject(VoiceService);
  private readonly changeDetector = inject(ChangeDetectorRef);

  @ViewChild('messagesContainer')
  messagesContainer?: ElementRef<HTMLDivElement>;

  private readonly apiUrl =
    'http://127.0.0.1:8000/api/chat';

  // Must exactly match the Firestore business document ID.
  businessId = 'demo_business_001';

  conversationId = signal('');

  messages = signal<ChatMessage[]>([]);

  messageInput = '';
  isSending = signal(false);
  errorMessage = signal('');
  appointmentId = signal<string | null>(null);

  isListening = signal(false);
  isSpeaking = signal(false);
  isVoiceMuted = signal(false);
  voiceStatus = signal('');
  voiceError = signal('');

  readonly voiceInputSupported =
    this.voiceService.isSpeechRecognitionSupported();

  readonly voiceOutputSupported =
    this.voiceService.isSpeechSynthesisSupported();

  suggestedMessages = [
    'What is your business name?',
    'What services do you offer?',
    'What are your opening hours?',
    'I want to book an appointment'
  ];

  constructor() {
    this.loadWelcomeMessage();
  }

  private loadWelcomeMessage(): void {
    this.isSending.set(true);

    const requestBody: ChatRequest = {
      message: 'Greet the customer using the saved welcome message and business name.',
      conversation_id: '',
      business_id: this.businessId
    };

    this.http
      .post<ChatResponse>(
        this.apiUrl,
        requestBody
      )
      .subscribe({
        next: response => {
          if (response.conversation_id) {
            this.conversationId.set(
              response.conversation_id
            );
          }

          this.messages.set([
            {
              id: crypto.randomUUID(),
              sender: 'assistant',
              message:
                response.reply ||
                'Hello! How can I help you today?',
              createdAt: new Date()
            }
          ]);

          this.isSending.set(false);
          this.scrollToBottom();
        },

        error: error => {
          console.error(
            'Welcome message request error:',
            error
          );

          this.messages.set([
            {
              id: crypto.randomUUID(),
              sender: 'assistant',
              message:
                'Hello! How can I help you today?',
              createdAt: new Date()
            }
          ]);

          this.isSending.set(false);
          this.scrollToBottom();
        }
      });
  }

  sendMessage(): void {
    const message = this.messageInput.trim();

    if (!message || this.isSending()) {
      return;
    }

    this.addMessage(
      'customer',
      message
    );

    this.messageInput = '';
    this.errorMessage.set('');
    this.isSending.set(true);

    const requestBody: ChatRequest = {
      message,
      conversation_id:
        this.conversationId(),
      business_id:
        this.businessId
    };

    console.log(
      'Chat request:',
      requestBody
    );

    this.http
      .post<ChatResponse>(
        this.apiUrl,
        requestBody
      )
      .subscribe({
        next: response => {
          console.log(
            'Chat response:',
            response
          );

          if (response.conversation_id) {
            this.conversationId.set(
              response.conversation_id
            );
          }

          const assistantReply =
            response.reply ||
            'Thank you. How else can I help?';

          this.addMessage(
            'assistant',
            assistantReply
          );

          this.speakAssistantReply(
            assistantReply
          );

          if (
            response.appointment_created &&
            response.appointment_id
          ) {
            this.appointmentId.set(
              response.appointment_id
            );
          }

          this.isSending.set(false);
          this.scrollToBottom();
        },

        error: error => {
          console.error(
            'Chat request error:',
            error
          );

          const backendMessage =
            error?.error?.detail;

          this.errorMessage.set(
            backendMessage ||
              'The AI receptionist is unavailable. Please try again.'
          );

          this.isSending.set(false);
          this.scrollToBottom();
        }
      });
  }

  toggleListening(): void {
    if (this.isSending()) {
      return;
    }

    if (this.isListening()) {
      this.stopListening();
      return;
    }

    this.voiceError.set('');
    this.voiceStatus.set('');

    this.voiceService.startListening({
      onStart: () => {
        this.isListening.set(true);
        this.voiceStatus.set('Listening...');
        this.changeDetector.markForCheck();
      },
      onResult: (transcript, isFinal) => {
        if (!transcript) {
          return;
        }

        this.messageInput = transcript;
        this.voiceStatus.set(
          isFinal ? 'Voice captured' : 'Listening...'
        );
        this.changeDetector.markForCheck();

        if (isFinal) {
          this.stopListening(false);
          setTimeout(() => this.sendMessage(), 100);
        }
      },
      onError: message => {
        this.isListening.set(false);
        this.voiceStatus.set('');

        if (message) {
          this.voiceError.set(message);
        }

        this.changeDetector.markForCheck();
      },
      onEnd: () => {
        this.isListening.set(false);

        if (this.voiceStatus() === 'Listening...') {
          this.voiceStatus.set('');
        }

        this.changeDetector.markForCheck();
      }
    });
  }

  stopListening(clearStatus = true): void {
    this.voiceService.stopListening();
    this.isListening.set(false);

    if (clearStatus) {
      this.voiceStatus.set('');
    }
  }

  toggleVoiceMute(): void {
    const muted = !this.isVoiceMuted();

    this.isVoiceMuted.set(muted);
    this.voiceService.setMuted(muted);
    this.isSpeaking.set(false);
    this.voiceStatus.set(
      muted ? 'AI voice muted' : 'AI voice enabled'
    );

    setTimeout(() => {
      if (
        this.voiceStatus() === 'AI voice muted' ||
        this.voiceStatus() === 'AI voice enabled'
      ) {
        this.voiceStatus.set('');
      }
    }, 1800);
  }

  dismissVoiceError(): void {
    this.voiceError.set('');
  }

  sendSuggestedMessage(
    message: string
  ): void {
    this.messageInput = message;
    this.sendMessage();
  }

  handleEnter(
    event: Event
  ): void {
    const keyboardEvent =
      event as KeyboardEvent;

    if (keyboardEvent.shiftKey) {
      return;
    }

    keyboardEvent.preventDefault();
    this.sendMessage();
  }

  startNewConversation(): void {
    this.stopListening();
    this.voiceService.stopSpeaking();
    this.isSpeaking.set(false);
    this.voiceError.set('');
    this.conversationId.set('');
    this.appointmentId.set(null);
    this.errorMessage.set('');
    this.messageInput = '';
    this.messages.set([]);

    this.loadWelcomeMessage();
  }

  ngOnDestroy(): void {
    this.voiceService.destroy();
  }

  formatTime(
    date: Date
  ): string {
    return new Intl.DateTimeFormat(
      'en-GB',
      {
        hour: '2-digit',
        minute: '2-digit'
      }
    ).format(date);
  }

  private speakAssistantReply(message: string): void {
    if (this.isVoiceMuted()) {
      return;
    }

    this.voiceService.speak(
      message,
      () => {
        this.isSpeaking.set(true);
        this.voiceStatus.set('AI is speaking...');
        this.changeDetector.markForCheck();
      },
      () => {
        this.isSpeaking.set(false);

        if (this.voiceStatus() === 'AI is speaking...') {
          this.voiceStatus.set('');
        }

        this.changeDetector.markForCheck();
      }
    );
  }

  private addMessage(
    sender: 'customer' | 'assistant',
    message: string
  ): void {
    this.messages.update(
      currentMessages => [
        ...currentMessages,
        {
          id: crypto.randomUUID(),
          sender,
          message,
          createdAt: new Date()
        }
      ]
    );

    this.scrollToBottom();
  }

  private scrollToBottom(): void {
    setTimeout(() => {
      const container =
        this.messagesContainer
          ?.nativeElement;

      if (container) {
        container.scrollTop =
          container.scrollHeight;
      }
    });
  }
}