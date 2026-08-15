import { Routes } from '@angular/router';

import {
  AdminDashboardComponent
} from './admin-dashboard/admin-dashboard';

import {
  ConversationsComponent
} from './conversations/conversations';

import {
  BookAppointmentComponent
} from './book-appointment/book-appointment';
import {
  ChatComponent
} from './chat/chat';
import {
  BusinessSettingsComponent
} from './business-settings/business-settings';

import {
  CustomersComponent
} from './customers/customers';

import {
  CustomerDetailsComponent
} from './customer-details/customer-details';


export const routes: Routes = [
  {
    path: 'admin',
    component: AdminDashboardComponent,
    title: 'AI Receptionist Admin'
  },
  {
    path: 'admin/customers',
    component: CustomersComponent,
    title: 'Customers'
  },
  {
    path: 'admin/customers/:customerId',
    component: CustomerDetailsComponent,
    title: 'Customer Details'
  },
  {
    path: 'admin/conversations',
    component: ConversationsComponent,
    title: 'Customer Conversations'
  },
  {
  path: 'book-appointment',
  component: BookAppointmentComponent,
  title: 'Book an Appointment'
},
{
  path: 'chat',
  component: ChatComponent,
  title: 'Chat with AI Receptionist'
},
{
  path: 'admin/business-settings',
  component: BusinessSettingsComponent
},
  {
    path: '',
    redirectTo: 'admin',
    pathMatch: 'full'
  },
  {
    path: '**',
    redirectTo: 'admin'
  }
];