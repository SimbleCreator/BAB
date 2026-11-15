import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { App } from './app';
import { routes } from './app.routes';

describe('App', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [App],
      providers: [provideRouter(routes), provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
  });

  it('renders the five bottom navigation tabs', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const tabs = Array.from(
      (fixture.nativeElement as HTMLElement).querySelectorAll('.bottom-nav .tab span'),
    ).map((el) => el.textContent?.trim());
    expect(tabs).toEqual(['Today', 'Activity', 'Train', 'Eat', 'More']);
  });
});
