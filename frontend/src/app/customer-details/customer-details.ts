import { CommonModule } from '@angular/common';
import { Component, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

interface Customer {
  id: string;
  business_id: string;
  name: string;
  phone: string;
  email: string | null;
  notes: string | null;
  total_appointments: number;
  last_appointment_date: string | null;
  last_appointment_id: string | null;
  created_at: string | null;
  updated_at: string | null;
}

interface CustomerAppointment {
  id: string;
  service: string;
  appointment_date: string;
  appointment_time: string;
  status: string;
  source: string;
  conversation_id: string | null;
  created_at: string | null;
}

interface CustomerDetailsResponse {
  customer: Customer;
  appointments: CustomerAppointment[];
  total_appointments: number;
}

@Component({
  selector: 'app-customer-details',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './customer-details.html',
  styleUrl: './customer-details.css'
})
export class CustomerDetailsComponent implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly apiUrl = 'http://127.0.0.1:8000/api/customers';

  customer = signal<Customer | null>(null);
  appointments = signal<CustomerAppointment[]>([]);
  isLoading = signal(false);
  isSaving = signal(false);
  isDeleting = signal(false);
  isEditing = signal(false);
  errorMessage = signal('');
  successMessage = signal('');

  editName = '';
  editPhone = '';
  editEmail = '';
  editNotes = '';

  ngOnInit(): void {
    this.loadCustomer();
  }

  loadCustomer(): void {
    const customerId = this.route.snapshot.paramMap.get('customerId');

    if (!customerId) {
      this.errorMessage.set('Customer ID is missing.');
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set('');

    this.http.get<CustomerDetailsResponse>(`${this.apiUrl}/${customerId}`).subscribe({
      next: response => {
        this.customer.set(response.customer);
        this.appointments.set(response.appointments ?? []);
        this.setEditValues(response.customer);
        this.isLoading.set(false);
      },
      error: error => {
        console.error('Customer details error:', error);
        this.errorMessage.set(error?.error?.detail ?? 'Customer could not be loaded.');
        this.isLoading.set(false);
      }
    });
  }

  startEditing(): void {
    const customer = this.customer();
    if (!customer) return;
    this.setEditValues(customer);
    this.isEditing.set(true);
    this.successMessage.set('');
    this.errorMessage.set('');
  }

  cancelEditing(): void {
    this.isEditing.set(false);
    const customer = this.customer();
    if (customer) this.setEditValues(customer);
  }

  saveCustomer(): void {
    const customer = this.customer();
    if (!customer || this.isSaving()) return;

    const name = this.editName.trim();
    const phone = this.editPhone.trim();

    if (name.length < 2 || phone.length < 7) {
      this.errorMessage.set('Enter a valid customer name and phone number.');
      return;
    }

    this.isSaving.set(true);
    this.errorMessage.set('');
    this.successMessage.set('');

    const payload = {
      business_id: customer.business_id,
      name,
      phone,
      email: this.editEmail.trim() || null,
      notes: this.editNotes.trim() || null
    };

    this.http.put(`${this.apiUrl}/${customer.id}`, payload).subscribe({
      next: () => {
        this.customer.set({ ...customer, ...payload });
        this.isEditing.set(false);
        this.isSaving.set(false);
        this.successMessage.set('Customer details updated successfully.');
      },
      error: error => {
        console.error('Customer update error:', error);
        this.errorMessage.set(error?.error?.detail ?? 'Customer could not be updated.');
        this.isSaving.set(false);
      }
    });
  }

  deleteCustomer(): void {
    const customer = this.customer();
    if (!customer || this.isDeleting()) return;

    const confirmed = window.confirm(
      `Delete ${customer.name}? Customers with appointment history cannot be deleted.`
    );

    if (!confirmed) return;

    this.isDeleting.set(true);
    this.errorMessage.set('');

    this.http.delete(`${this.apiUrl}/${customer.id}`).subscribe({
      next: () => {
        void this.router.navigate(['/admin/customers']);
      },
      error: error => {
        console.error('Customer delete error:', error);
        this.errorMessage.set(error?.error?.detail ?? 'Customer could not be deleted.');
        this.isDeleting.set(false);
      }
    });
  }

  getInitials(name: string): string {
    return name.trim().split(/\s+/).slice(0, 2)
      .map(part => part.charAt(0).toUpperCase()).join('') || 'CU';
  }

  formatDate(value: string | null): string {
    if (!value) return 'Not available';
    const date = new Date(value.length === 10 ? `${value}T00:00:00` : value);
    if (Number.isNaN(date.getTime())) return value;
    return new Intl.DateTimeFormat('en-GB', {
      day: '2-digit', month: 'short', year: 'numeric'
    }).format(date);
  }

  formatStatus(status: string): string {
    return status ? status.charAt(0).toUpperCase() + status.slice(1) : 'Pending';
  }

  private setEditValues(customer: Customer): void {
    this.editName = customer.name ?? '';
    this.editPhone = customer.phone ?? '';
    this.editEmail = customer.email ?? '';
    this.editNotes = customer.notes ?? '';
  }
}
