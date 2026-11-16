import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { vi } from 'vitest';

import { apiErrorMessage } from './api-error';
import { WAKE_DELAYS_MS, isWaking, wakeRetryInterceptor } from './wake-retry.interceptor';

const URL = '/api/v1/profile';

describe('wakeRetryInterceptor', () => {
  let http: HttpClient;
  let ctrl: HttpTestingController;

  beforeEach(() => {
    vi.useFakeTimers();
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([wakeRetryInterceptor])),
        provideHttpClientTesting(),
      ],
    });
    http = TestBed.inject(HttpClient);
    ctrl = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    ctrl.verify();
    vi.useRealTimers();
  });

  it('retries a GET while the server wakes up', () => {
    let body: unknown;
    http.get(URL).subscribe((b) => (body = b));
    ctrl.expectOne(URL).flush('<html>', { status: 502, statusText: 'Bad Gateway' });
    vi.advanceTimersByTime(WAKE_DELAYS_MS[0]);
    ctrl.expectOne(URL).flush(null, { status: 524, statusText: 'Timeout' });
    vi.advanceTimersByTime(WAKE_DELAYS_MS[1]);
    ctrl.expectOne(URL).flush({ ok: true });
    expect(body).toEqual({ ok: true });
  });

  it('gives up after the last pause with a clear message', () => {
    let error: unknown;
    http.get(URL).subscribe({ error: (e) => (error = e) });
    for (const ms of WAKE_DELAYS_MS) {
      ctrl.expectOne(URL).flush(null, { status: 503, statusText: 'Unavailable' });
      vi.advanceTimersByTime(ms);
    }
    ctrl.expectOne(URL).flush(null, { status: 503, statusText: 'Unavailable' });
    expect(apiErrorMessage(error)).toContain('waking up');
  });

  it('never repeats a POST that may have reached the server', () => {
    let error: unknown;
    http
      .post('/api/v1/nutrition/days/2026-11-17/items', {})
      .subscribe({ error: (e) => (error = e) });
    ctrl
      .expectOne('/api/v1/nutrition/days/2026-11-17/items')
      .flush(null, { status: 504, statusText: 'Timeout' });
    vi.advanceTimersByTime(60000);
    expect(error).toBeTruthy();
  });

  it('retries sign-in, and not B.A.B errors that carry a code', () => {
    http.post('/api/v1/auth/login', {}).subscribe({ error: () => undefined });
    ctrl.expectOne('/api/v1/auth/login').flush(null, { status: 502, statusText: 'Bad Gateway' });
    vi.advanceTimersByTime(WAKE_DELAYS_MS[0]);
    ctrl.expectOne('/api/v1/auth/login').flush({ access_token: 'x' });

    let error: unknown;
    http.get(URL).subscribe({ error: (e) => (error = e) });
    ctrl
      .expectOne(URL)
      .flush({ detail: 'Bounce is busy.', code: 'model_busy' }, { status: 502, statusText: 'x' });
    expect(isWaking(error)).toBe(false);
    expect(apiErrorMessage(error)).toBe('Bounce is busy.');
  });
});
