import { CommonModule } from '@angular/common';
import { Component, OnInit, signal } from '@angular/core';
import {
  FormBuilder,
  FormGroup,
  ReactiveFormsModule,
  Validators
} from '@angular/forms';
import { HttpClient } from '@angular/common/http';

interface BusinessService {
  id: string;
  name: string;
  description: string | null;
  duration_minutes: number;
  active: boolean;
}

interface ServicesResponse {
  services: BusinessService[];
  total: number;
}

@Component({
  selector: 'app-business-settings',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule
  ],
  templateUrl: './business-settings.html',
  styleUrl: './business-settings.css'
})
export class BusinessSettingsComponent implements OnInit {
  private readonly apiBaseUrl =
    'http://127.0.0.1:8000/api';

  readonly businessId = 'demo_business_001';

  readonly loading = signal(false);
  readonly saving = signal(false);
  readonly serviceSaving = signal(false);

  readonly successMessage = signal('');
  readonly errorMessage = signal('');

  readonly services = signal<BusinessService[]>([]);
  readonly editingServiceId = signal<string | null>(null);

  readonly days = [
    {
      key: 'monday',
      label: 'Monday'
    },
    {
      key: 'tuesday',
      label: 'Tuesday'
    },
    {
      key: 'wednesday',
      label: 'Wednesday'
    },
    {
      key: 'thursday',
      label: 'Thursday'
    },
    {
      key: 'friday',
      label: 'Friday'
    },
    {
      key: 'saturday',
      label: 'Saturday'
    },
    {
      key: 'sunday',
      label: 'Sunday'
    }
  ];

  readonly settingsForm: FormGroup;
  readonly serviceForm: FormGroup;

  constructor(
    private readonly formBuilder: FormBuilder,
    private readonly http: HttpClient
  ) {
    this.settingsForm = this.formBuilder.group({
      business_name: [
        '',
        [
          Validators.required,
          Validators.minLength(2)
        ]
      ],

      business_type: [
        '',
        [
          Validators.required,
          Validators.minLength(2)
        ]
      ],

      address: [''],
      phone: [''],

      email: [
        '',
        [
          Validators.email
        ]
      ],

      website: [''],

      timezone: [
        'Europe/London',
        [
          Validators.required
        ]
      ],

      welcome_message: [
        '',
        [
          Validators.required,
          Validators.minLength(2)
        ]
      ],

      booking_message: [''],

      working_hours: this.formBuilder.group({
        monday: this.createWorkingDay(true),
        tuesday: this.createWorkingDay(true),
        wednesday: this.createWorkingDay(true),
        thursday: this.createWorkingDay(true),
        friday: this.createWorkingDay(true),
        saturday: this.createWorkingDay(true),
        sunday: this.createWorkingDay(false)
      })
    });

    this.serviceForm = this.formBuilder.group({
      name: [
        '',
        [
          Validators.required,
          Validators.minLength(2)
        ]
      ],

      description: [''],

      duration_minutes: [
        60,
        [
          Validators.required,
          Validators.min(5),
          Validators.max(1440)
        ]
      ],

      active: [true]
    });
  }

  ngOnInit(): void {
    this.loadSettings();
    this.loadServices();
  }

  private createWorkingDay(
    isOpen: boolean
  ): FormGroup {
    return this.formBuilder.group({
      open: [isOpen],
      start: [
        isOpen ? '09:00' : null
      ],
      end: [
        isOpen ? '18:00' : null
      ]
    });
  }

  get workingHoursGroup(): FormGroup {
    return this.settingsForm.get(
      'working_hours'
    ) as FormGroup;
  }

  getDayGroup(dayKey: string): FormGroup {
    return this.workingHoursGroup.get(
      dayKey
    ) as FormGroup;
  }

  loadSettings(): void {
    this.loading.set(true);
    this.errorMessage.set('');
    this.successMessage.set('');

    const url =
      `${this.apiBaseUrl}/business-settings/` +
      `${this.businessId}`;

    this.http.get<any>(url).subscribe({
      next: response => {
        this.settingsForm.patchValue({
          business_name:
            response.business_name ?? '',

          business_type:
            response.business_type ?? '',

          address:
            response.address ?? '',

          phone:
            response.phone ?? '',

          email:
            response.email ?? '',

          website:
            response.website ?? '',

          timezone:
            response.timezone ??
            'Europe/London',

          welcome_message:
            response.welcome_message ?? '',

          booking_message:
            response.booking_message ?? '',

          working_hours:
            response.working_hours ?? {}
        });

        this.loading.set(false);
      },

      error: error => {
        console.error(
          'Load business settings error:',
          error
        );

        this.errorMessage.set(
          error.error?.detail ??
          'Business settings could not be loaded.'
        );

        this.loading.set(false);
      }
    });
  }

  saveSettings(): void {
    this.successMessage.set('');
    this.errorMessage.set('');

    if (this.settingsForm.invalid) {
      this.settingsForm.markAllAsTouched();

      this.errorMessage.set(
        'Please complete all required fields.'
      );

      return;
    }

    this.saving.set(true);

    const payload =
      this.settingsForm.getRawValue();

    const url =
      `${this.apiBaseUrl}/business-settings/` +
      `${this.businessId}`;

    this.http.put(url, payload).subscribe({
      next: () => {
        this.successMessage.set(
          'Business settings saved successfully.'
        );

        this.saving.set(false);
      },

      error: error => {
        console.error(
          'Save business settings error:',
          error
        );

        this.errorMessage.set(
          error.error?.detail ??
          'Business settings could not be saved.'
        );

        this.saving.set(false);
      }
    });
  }

  loadServices(): void {
    this.errorMessage.set('');

    const url =
      `${this.apiBaseUrl}/business-settings/` +
      `${this.businessId}/services`;

    this.http
      .get<ServicesResponse>(url)
      .subscribe({
        next: response => {
          this.services.set(
            response.services ?? []
          );
        },

        error: error => {
          console.error(
            'Load services error:',
            error
          );

          this.errorMessage.set(
            error.error?.detail ??
            'Services could not be loaded.'
          );
        }
      });
  }

  saveService(): void {
    this.successMessage.set('');
    this.errorMessage.set('');

    if (this.serviceForm.invalid) {
      this.serviceForm.markAllAsTouched();

      this.errorMessage.set(
        'Please enter valid service details.'
      );

      return;
    }

    this.serviceSaving.set(true);

    const payload =
      this.serviceForm.getRawValue();

    const serviceId =
      this.editingServiceId();

    let request;

    if (serviceId) {
      const url =
        `${this.apiBaseUrl}/business-settings/` +
        `${this.businessId}/services/` +
        `${serviceId}`;

      request = this.http.put(
        url,
        payload
      );
    } else {
      const url =
        `${this.apiBaseUrl}/business-settings/` +
        `${this.businessId}/services`;

      request = this.http.post(
        url,
        payload
      );
    }

    request.subscribe({
      next: () => {
        this.successMessage.set(
          serviceId
            ? 'Service updated successfully.'
            : 'Service created successfully.'
        );

        this.resetServiceForm();
        this.loadServices();

        this.serviceSaving.set(false);
      },

      error: error => {
        console.error(
          'Save service error:',
          error
        );

        this.errorMessage.set(
          error.error?.detail ??
          'Service could not be saved.'
        );

        this.serviceSaving.set(false);
      }
    });
  }

  editService(
    service: BusinessService
  ): void {
    this.editingServiceId.set(
      service.id
    );

    this.serviceForm.patchValue({
      name:
        service.name,

      description:
        service.description ?? '',

      duration_minutes:
        service.duration_minutes,

      active:
        service.active
    });

    window.scrollTo({
      top: document.body.scrollHeight,
      behavior: 'smooth'
    });
  }

  resetServiceForm(): void {
    this.editingServiceId.set(null);

    this.serviceForm.reset({
      name: '',
      description: '',
      duration_minutes: 60,
      active: true
    });
  }

  toggleService(
    service: BusinessService
  ): void {
    this.successMessage.set('');
    this.errorMessage.set('');

    const url =
      `${this.apiBaseUrl}/business-settings/` +
      `${this.businessId}/services/` +
      `${service.id}/status`;

    this.http.patch(
      url,
      {
        active: !service.active
      }
    ).subscribe({
      next: () => {
        this.successMessage.set(
          service.active
            ? 'Service disabled successfully.'
            : 'Service enabled successfully.'
        );

        this.loadServices();
      },

      error: error => {
        console.error(
          'Update service status error:',
          error
        );

        this.errorMessage.set(
          error.error?.detail ??
          'Service status could not be updated.'
        );
      }
    });
  }

  deleteService(
    service: BusinessService
  ): void {
    this.successMessage.set('');
    this.errorMessage.set('');

    const confirmed = window.confirm(
      `Are you sure you want to delete "${service.name}"?`
    );

    if (!confirmed) {
      return;
    }

    const url =
      `${this.apiBaseUrl}/business-settings/` +
      `${this.businessId}/services/` +
      `${service.id}`;

    this.http.delete(url).subscribe({
      next: () => {
        this.successMessage.set(
          'Service deleted successfully.'
        );

        if (
          this.editingServiceId() === service.id
        ) {
          this.resetServiceForm();
        }

        this.loadServices();
      },

      error: error => {
        console.error(
          'Delete service error:',
          error
        );

        this.errorMessage.set(
          error.error?.detail ??
          'Service could not be deleted.'
        );
      }
    });
  }

  clearMessages(): void {
    this.successMessage.set('');
    this.errorMessage.set('');
  }
}