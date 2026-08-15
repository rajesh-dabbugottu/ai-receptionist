import { ComponentFixture, TestBed } from '@angular/core/testing';

import { BusinessSettings } from './business-settings';

describe('BusinessSettings', () => {
  let component: BusinessSettings;
  let fixture: ComponentFixture<BusinessSettings>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [BusinessSettings],
    }).compileComponents();

    fixture = TestBed.createComponent(BusinessSettings);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
