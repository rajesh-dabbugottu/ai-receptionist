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
import { RouterLink } from '@angular/router';


type AppointmentStatus =
  | 'pending'
  | 'confirmed'
  | 'cancelled'
  | 'completed';


interface Appointment {
  id: string;
  business_id: string | null;
  conversation_id: string | null;
  customer_name: string;
  customer_phone: string;
  service: string;
  appointment_date: string;
  appointment_time: string;
  status: AppointmentStatus;
  source: string;
  created_at: string | null;
  updated_at: string | null;
}


interface AppointmentResponse {
  appointments: Appointment[];
  total: number;
}


@Component({
  selector: 'app-admin-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterLink
  ],
  templateUrl: './admin-dashboard.html',
  styleUrl: './admin-dashboard.css'
})
export class AdminDashboardComponent implements OnInit {
  private readonly http = inject(HttpClient);

  private readonly apiUrl =
    'http://127.0.0.1:8000/api/appointments';

  appointments = signal<Appointment[]>([]);
  searchTerm = signal('');
  selectedStatus = signal('all');
  isLoading = signal(false);
  errorMessage = signal('');
  successMessage = signal('');
  updatingAppointmentId = signal<string | null>(null);

  totalAppointments = computed(
    () => this.appointments().length
  );

  pendingAppointments = computed(
    () => this.appointments().filter(
      appointment => appointment.status === 'pending'
    ).length
  );

  confirmedAppointments = computed(
    () => this.appointments().filter(
      appointment => appointment.status === 'confirmed'
    ).length
  );

  cancelledAppointments = computed(
    () => this.appointments().filter(
      appointment => appointment.status === 'cancelled'
    ).length
  );

  todayAppointments = computed(() => {
    const today = new Date()
      .toISOString()
      .split('T')[0];

    return this.appointments().filter(
      appointment =>
        appointment.appointment_date === today
    ).length;
  });

  filteredAppointments = computed(() => {
    const search = this.searchTerm()
      .trim()
      .toLowerCase();

    const status = this.selectedStatus();

    return this.appointments().filter(
      appointment => {
        const matchesStatus =
          status === 'all' ||
          appointment.status === status;

        const searchableText = [
          appointment.customer_name,
          appointment.customer_phone,
          appointment.service,
          appointment.appointment_date,
          appointment.appointment_time,
          appointment.status
        ]
          .join(' ')
          .toLowerCase();

        const matchesSearch =
          !search ||
          searchableText.includes(search);

        return matchesStatus && matchesSearch;
      }
    );
  });

  ngOnInit(): void {
    this.loadAppointments();
  }

  loadAppointments(): void {
    this.isLoading.set(true);
    this.errorMessage.set('');
    this.successMessage.set('');

    this.http
      .get<AppointmentResponse>(this.apiUrl)
      .subscribe({
        next: response => {
          this.appointments.set(
            response.appointments ?? []
          );

          this.isLoading.set(false);
        },
        error: error => {
          console.error(
            'Appointments loading error:',
            error
          );

          this.errorMessage.set(
            'Appointments could not be loaded. ' +
            'Check that the FastAPI backend is running.'
          );

          this.isLoading.set(false);
        }
      });
  }

  updateSearch(value: string): void {
    this.searchTerm.set(value);
  }

  updateStatusFilter(value: string): void {
    this.selectedStatus.set(value);
  }

  updateAppointmentStatus(
    appointment: Appointment,
    status: AppointmentStatus
  ): void {
    if (appointment.status === status) {
      return;
    }

    const action =
      status === 'confirmed'
        ? 'confirm'
        : status === 'cancelled'
          ? 'cancel'
          : 'update';

    const shouldContinue = window.confirm(
      `Are you sure you want to ${action} ` +
      `${appointment.customer_name}'s appointment?`
    );

    if (!shouldContinue) {
      return;
    }

    this.updatingAppointmentId.set(
      appointment.id
    );

    this.errorMessage.set('');
    this.successMessage.set('');

    this.http
      .patch(
        `${this.apiUrl}/${appointment.id}/status`,
        { status }
      )
      .subscribe({
        next: () => {
          this.appointments.update(
            appointments =>
              appointments.map(item =>
                item.id === appointment.id
                  ? {
                      ...item,
                      status
                    }
                  : item
              )
          );

          this.successMessage.set(
            `${appointment.customer_name}'s ` +
            `appointment was marked as ${status}.`
          );

          this.updatingAppointmentId.set(null);
        },
        error: error => {
          console.error(
            'Status update error:',
            error
          );

          this.errorMessage.set(
            'The appointment status could not be updated.'
          );

          this.updatingAppointmentId.set(null);
        }
      });
  }

  formatDate(date: string): string {
    if (!date) {
      return 'Not provided';
    }

    const parsedDate = new Date(
      `${date}T00:00:00`
    );

    if (Number.isNaN(parsedDate.getTime())) {
      return date;
    }

    return new Intl.DateTimeFormat(
      'en-GB',
      {
        day: '2-digit',
        month: 'short',
        year: 'numeric'
      }
    ).format(parsedDate);
  }

  formatTime(time: string): string {
    if (!time) {
      return 'Not provided';
    }

    const [hours, minutes] = time
      .split(':')
      .map(Number);

    if (
      Number.isNaN(hours) ||
      Number.isNaN(minutes)
    ) {
      return time;
    }

    const date = new Date();

    date.setHours(hours, minutes, 0, 0);

    return new Intl.DateTimeFormat(
      'en-GB',
      {
        hour: '2-digit',
        minute: '2-digit'
      }
    ).format(date);
  }

  getInitials(name: string): string {
    if (!name) {
      return 'NA';
    }

    return name
      .trim()
      .split(/\s+/)
      .slice(0, 2)
      .map(word => word.charAt(0).toUpperCase())
      .join('');
  }
}