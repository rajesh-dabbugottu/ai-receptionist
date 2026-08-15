import {
  Component,
  computed,
  inject,
  OnInit,
  signal
} from '@angular/core';

import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';


interface ConversationSummary {
  conversation_id: string;
  business_id: string | null;
  customer_name: string;
  last_message: string;
  status: string;
  intent: string;
  appointment_created: boolean;
  appointment_id: string | null;
  created_at: string | null;
  updated_at: string | null;
}


interface ConversationMessage {
  id: string;
  sender: string;
  message: string;
  intent: string | null;
  booking_ready: boolean;
  created_at: string | null;
}


interface ConversationsResponse {
  conversations: ConversationSummary[];
  total: number;
}


interface ConversationDetails {
  conversation_id: string;
  business_id: string | null;
  status: string;
  intent: string;
  appointment_created: boolean;
  appointment_id: string | null;
  created_at: string | null;
  updated_at: string | null;
  messages: ConversationMessage[];
}


@Component({
  selector: 'app-conversations',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule
  ],
  templateUrl: './conversations.html',
  styleUrl: './conversations.css'
})
export class ConversationsComponent implements OnInit {
  private readonly http = inject(HttpClient);

  private readonly apiUrl =
    'https://ai-receptionist-a0b0.onrender.com/api/conversations';

  conversations = signal<ConversationSummary[]>([]);
  selectedConversation = signal<ConversationDetails | null>(
    null
  );

  selectedConversationId = signal<string | null>(null);

  searchTerm = signal('');
  isLoadingList = signal(false);
  isLoadingMessages = signal(false);
  errorMessage = signal('');

  filteredConversations = computed(() => {
    const search = this.searchTerm()
      .trim()
      .toLowerCase();

    if (!search) {
      return this.conversations();
    }

    return this.conversations().filter(
      conversation => {
        const searchableText = [
          conversation.customer_name,
          conversation.last_message,
          conversation.status,
          conversation.intent,
          conversation.conversation_id
        ]
          .join(' ')
          .toLowerCase();

        return searchableText.includes(search);
      }
    );
  });

  ngOnInit(): void {
    this.loadConversations();
  }

  loadConversations(): void {
    this.isLoadingList.set(true);
    this.errorMessage.set('');

    this.http
      .get<ConversationsResponse>(this.apiUrl)
      .subscribe({
        next: response => {
          const conversations =
            response.conversations ?? [];

          this.conversations.set(conversations);
          this.isLoadingList.set(false);

          if (
            conversations.length > 0 &&
            !this.selectedConversationId()
          ) {
            this.openConversation(
              conversations[0].conversation_id
            );
          }
        },
        error: error => {
          console.error(
            'Conversation list error:',
            error
          );

          this.errorMessage.set(
            'Conversations could not be loaded. ' +
            'Check that FastAPI is running.'
          );

          this.isLoadingList.set(false);
        }
      });
  }

  openConversation(conversationId: string): void {
    this.selectedConversationId.set(conversationId);
    this.isLoadingMessages.set(true);
    this.errorMessage.set('');

    this.http
      .get<ConversationDetails>(
        `${this.apiUrl}/${conversationId}`
      )
      .subscribe({
        next: response => {
          this.selectedConversation.set(response);
          this.isLoadingMessages.set(false);

          setTimeout(() => {
            this.scrollToBottom();
          });
        },
        error: error => {
          console.error(
            'Conversation details error:',
            error
          );

          this.errorMessage.set(
            'The selected conversation could not be loaded.'
          );

          this.isLoadingMessages.set(false);
        }
      });
  }

  updateSearch(value: string): void {
    this.searchTerm.set(value);
  }

  refresh(): void {
    const selectedId = this.selectedConversationId();

    this.loadConversations();

    if (selectedId) {
      this.openConversation(selectedId);
    }
  }

  getInitials(name: string): string {
    if (!name) {
      return 'WV';
    }

    return name
      .trim()
      .split(/\s+/)
      .slice(0, 2)
      .map(word => word.charAt(0).toUpperCase())
      .join('');
  }

  formatDateTime(value: string | null): string {
    if (!value) {
      return '';
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
      return '';
    }

    return new Intl.DateTimeFormat(
      'en-GB',
      {
        day: '2-digit',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit'
      }
    ).format(date);
  }

  formatListTime(value: string | null): string {
    if (!value) {
      return '';
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
      return '';
    }

    const today = new Date();

    const isToday =
      date.toDateString() === today.toDateString();

    if (isToday) {
      return new Intl.DateTimeFormat(
        'en-GB',
        {
          hour: '2-digit',
          minute: '2-digit'
        }
      ).format(date);
    }

    return new Intl.DateTimeFormat(
      'en-GB',
      {
        day: '2-digit',
        month: 'short'
      }
    ).format(date);
  }

  isCustomer(sender: string): boolean {
    return sender === 'customer' || sender === 'user';
  }

  private scrollToBottom(): void {
    const messageArea = document.querySelector(
      '.messages-area'
    );

    if (messageArea) {
      messageArea.scrollTop = messageArea.scrollHeight;
    }
  }

  getCustomerName(
  conversationId: string | null | undefined
): string {
  if (!conversationId) {
    return 'Website Visitor';
  }

  const conversation = this.conversations().find(
    item => item.conversation_id === conversationId
  );

  return conversation?.customer_name || 'Website Visitor';
}
}