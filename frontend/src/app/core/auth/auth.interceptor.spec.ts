import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { environment } from '../../../environments/environment';
import { TokenOut } from '../api/models';
import { authInterceptor } from './auth.interceptor';
import { AuthService } from './auth.service';

const API = environment.apiBaseUrl;

function token(value: string): TokenOut {
  return {
    access_token: value,
    token_type: 'bearer',
    expires_in: 900,
    user: { id: 1, email: 'a@example.com', is_admin: false, created_at: '', has_profile: true },
  };
}

describe('authInterceptor', () => {
  let http: HttpClient;
  let ctrl: HttpTestingController;
  let auth: AuthService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideRouter([{ path: 'login', children: [] }]),
        provideHttpClient(withInterceptors([authInterceptor])),
        provideHttpClientTesting(),
      ],
    });
    http = TestBed.inject(HttpClient);
    ctrl = TestBed.inject(HttpTestingController);
    auth = TestBed.inject(AuthService);
  });

  afterEach(() => ctrl.verify());

  function signIn(): void {
    auth.login({ email: 'a@example.com', password: 'x' }).subscribe();
    ctrl.expectOne(`${API}/auth/login`).flush(token('old'));
  }

  it('adds the bearer token and sends cookies', () => {
    signIn();
    http.get(`${API}/profile`).subscribe();
    const req = ctrl.expectOne(`${API}/profile`);
    expect(req.request.headers.get('Authorization')).toBe('Bearer old');
    expect(req.request.withCredentials).toBe(true);
    expect(req.request.headers.get('X-BAB-Client')).toBe('web');
    req.flush({});
  });

  it('refreshes once on 401 and retries with the new token', () => {
    signIn();
    let body: unknown;
    http.get(`${API}/profile`).subscribe((b) => (body = b));
    ctrl.expectOne(`${API}/profile`).flush({}, { status: 401, statusText: 'Unauthorized' });
    ctrl.expectOne(`${API}/auth/refresh`).flush(token('new'));
    const retry = ctrl.expectOne(`${API}/profile`);
    expect(retry.request.headers.get('Authorization')).toBe('Bearer new');
    retry.flush({ ok: true });
    expect(body).toEqual({ ok: true });
  });

  it('shares one refresh between concurrent 401s', () => {
    signIn();
    http.get(`${API}/a`).subscribe();
    http.get(`${API}/b`).subscribe();
    ctrl.expectOne(`${API}/a`).flush({}, { status: 401, statusText: 'Unauthorized' });
    ctrl.expectOne(`${API}/b`).flush({}, { status: 401, statusText: 'Unauthorized' });
    ctrl.expectOne(`${API}/auth/refresh`).flush(token('new'));
    ctrl.expectOne(`${API}/a`).flush({});
    ctrl.expectOne(`${API}/b`).flush({});
  });

  it('ends the session when the refresh fails', () => {
    signIn();
    let failed = false;
    http.get(`${API}/profile`).subscribe({ error: () => (failed = true) });
    ctrl.expectOne(`${API}/profile`).flush({}, { status: 401, statusText: 'Unauthorized' });
    ctrl.expectOne(`${API}/auth/refresh`).flush({}, { status: 401, statusText: 'Unauthorized' });
    expect(failed).toBe(true);
    expect(auth.isLoggedIn()).toBe(false);
  });

  it('leaves other hosts alone', () => {
    signIn();
    http.get('https://tile.openstreetmap.org/1/1/1.png').subscribe();
    const req = ctrl.expectOne('https://tile.openstreetmap.org/1/1/1.png');
    expect(req.request.headers.has('Authorization')).toBe(false);
    req.flush({});
  });
});
