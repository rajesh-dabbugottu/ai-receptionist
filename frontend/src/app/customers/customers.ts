import {
  Component,
  computed,
  inject,
  OnInit,
  signal
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient, HttpParams } from '@angular/common/http';
import { RouterLink } from '@angular/router';

interface Customer {
  id: string;
  business_id: string | null;
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

interface CustomersResponse {
  customers: Customer[];
  total: number;
}

@Component({
  selector: 'app-customers',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './customers.html',
  styleUrl: './customers.css'
})
export class CustomersComponent implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = 'http://127.0.0.1:8000/api/customers';
  private readonly businessId = 'demo_business_001';

  customers = signal<Customer[]>([]);
  searchTerm = signal('');
  isLoading = signal(false);
  errorMessage = signal('');

  filteredCustomers = computed(() => {
    const search = this.searchTerm().trim().toLowerCase();

    if (!search) {
      return this.customers();
    }

    return this.customers().filter(customer =>
      [customer.name, customer.phone, customer.email ?? '']
        .join(' ')
        .toLowerCase()
        .includes(search)
    );
  });

  totalAppointments = computed(() =>
    this.customers().reduce(
      (total, customer) => total + (customer.total_appointments ?? 0),
      0
    )
  );

  ngOnInit(): void {
    this.loadCustomers();
  }

  loadCustomers(): void {
    this.isLoading.set(true);
    this.errorMessage.set('');

    const params = new HttpParams().set('business_id', this.businessId);

    this.http.get<CustomersResponse>(this.apiUrl, { params }).subscribe({
      next: response => {
        this.customers.set(response.customers ?? []);
        this.isLoading.set(false);
      },
      error: error => {
        console.error('Customers loading error:', error);
        this.errorMessage.set(
          error?.error?.detail ??
          'Customers could not be loaded. Check that the FastAPI backend is running.'
        );
        this.isLoading.set(false);
      }
    });
  }

  updateSearch(value: string): void {
    this.searchTerm.set(value);
  }

  getInitials(name: string): string {
    const initials = name
      .trim()
      .split(/\s+/)
      .slice(0, 2)
      .map(part => part.charAt(0).toUpperCase())
      .join('');

    return initials || 'CU';
  }

  formatDate(value: string | null): string {
    if (!value) {
      return 'No appointments';
    }

    const parsed = new Date(`${value}T00:00:00`);

    if (Number.isNaN(parsed.getTime())) {
      return value;
    }

    return new Intl.DateTimeFormat('en-GB', {
      day: '2-digit',
      month: 'short',
      year: 'numeric'
    }).format(parsed);
  }
}
