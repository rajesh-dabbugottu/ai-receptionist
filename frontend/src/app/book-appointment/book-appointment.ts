import {
  Component,
  computed,
  inject,
  signal
} from '@angular/core';

import { CommonModule } from '@angular/common';

import {
  FormBuilder,
  ReactiveFormsModule,
  Validators
} from '@angular/forms';

import { HttpClient } from '@angular/common/http';


interface BookingResponse {
  success: boolean;
  message: string;
  appointment_id: string;
  status: string;
}


@Component({
  selector: 'app-book-appointment',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    
  ],
  templateUrl: './book-appointment.html',
  styleUrl: './book-appointment.css'
})
export class BookAppointmentComponent {
  private readonly formBuilder = inject(FormBuilder);
  private readonly http = inject(HttpClient);

  private readonly apiUrl =
    'https://ai-receptionist-a0b0.onrender.com/api/appointments';

  services = [
    'General Consultation',
    'Initial Assessment',
    'Follow-up Appointment',
    'Technical Support',
    'Business Consultation'
  ];

  availableTimes = [
    '09:00',
    '09:30',
    '10:00',
    '10:30',
    '11:00',
    '11:30',
    '12:00',
    '13:00',
    '13:30',
    '14:00',
    '14:30',
    '15:00',
    '15:30',
    '16:00',
    '16:30',
    '17:00'
  ];

  isSubmitting = signal(false);
  errorMessage = signal('');
  appointmentId = signal('');
  bookingStatus = signal('');

  bookingSuccessful = computed(
    () => this.appointmentId().length > 0
  );

  minimumDate = this.getTodayDate();

  bookingForm = this.formBuilder.nonNullable.group({
    customer_name: [
      '',
      [
        Validators.required,
        Validators.minLength(2),
        Validators.maxLength(100)
      ]
    ],

    customer_phone: [
      '',
      [
        Validators.required,
        Validators.minLength(7),
        Validators.maxLength(20),
        Validators.pattern(/^[0-9+\s()-]+$/)
      ]
    ],

    customer_email: [
      '',
      [
        Validators.email,
        Validators.maxLength(150)
      ]
    ],

    service: [
      '',
      Validators.required
    ],

    appointment_date: [
      '',
      Validators.required
    ],

    appointment_time: [
      '',
      Validators.required
    ],

    notes: [
      '',
      Validators.maxLength(500)
    ]
  });

  submitBooking(): void {
    this.errorMessage.set('');

    if (this.bookingForm.invalid) {
      this.bookingForm.markAllAsTouched();

      this.errorMessage.set(
        'Please complete all required fields correctly.'
      );

      return;
    }

    const selectedDate =
      this.bookingForm.controls
        .appointment_date.value;

    if (
      selectedDate &&
      selectedDate < this.minimumDate
    ) {
      this.errorMessage.set(
        'Please select today or a future date.'
      );

      return;
    }

    this.isSubmitting.set(true);

    const formValue = this.bookingForm.getRawValue();

    const requestBody = {
      business_id: 'demo_business',

      customer_name:
        formValue.customer_name.trim(),

      customer_phone:
        formValue.customer_phone.trim(),

      customer_email:
        formValue.customer_email.trim() || null,

      service:
        formValue.service,

      appointment_date:
        formValue.appointment_date,

      appointment_time:
        formValue.appointment_time,

      notes:
        formValue.notes.trim() || null
    };

    this.http
      .post<BookingResponse>(
        this.apiUrl,
        requestBody
      )
      .subscribe({
        next: response => {
          this.isSubmitting.set(false);

          this.appointmentId.set(
            response.appointment_id
          );

          this.bookingStatus.set(
            response.status
          );

          window.scrollTo({
            top: 0,
            behavior: 'smooth'
          });
        },

        error: error => {
          console.error(
            'Appointment booking error:',
            error
          );

          const backendMessage =
            error?.error?.detail;

          this.errorMessage.set(
            backendMessage ||
            'Your appointment could not be booked. Please try again.'
          );

          this.isSubmitting.set(false);
        }
      });
  }

  bookAnotherAppointment(): void {
    this.appointmentId.set('');
    this.bookingStatus.set('');
    this.errorMessage.set('');

    this.bookingForm.reset({
      customer_name: '',
      customer_phone: '',
      customer_email: '',
      service: '',
      appointment_date: '',
      appointment_time: '',
      notes: ''
    });
  }

  hasError(
    controlName:
      | 'customer_name'
      | 'customer_phone'
      | 'customer_email'
      | 'service'
      | 'appointment_date'
      | 'appointment_time'
      | 'notes',
    errorName?: string
  ): boolean {
    const control =
      this.bookingForm.controls[controlName];

    if (
      !control.touched &&
      !control.dirty
    ) {
      return false;
    }

    if (errorName) {
      return control.hasError(errorName);
    }

    return control.invalid;
  }

  private getTodayDate(): string {
    const today = new Date();

    const year = today.getFullYear();

    const month = String(
      today.getMonth() + 1
    ).padStart(2, '0');

    const day = String(
      today.getDate()
    ).padStart(2, '0');

    return `${year}-${month}-${day}`;
  }
}