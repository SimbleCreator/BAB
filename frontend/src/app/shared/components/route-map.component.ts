import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  OnDestroy,
  afterRenderEffect,
  input,
  viewChild,
} from '@angular/core';
import * as L from 'leaflet';

import { TrackPointOut } from '../../core/api/models';

const LEAFLET_CSS_ID = 'leaflet-css';

/** Leaflet's stylesheet is built as a separate file and only loaded when a map is shown. */
function ensureLeafletCss(): Promise<void> {
  const existing = document.getElementById(LEAFLET_CSS_ID) as HTMLLinkElement | null;
  if (existing) {
    return existing.sheet
      ? Promise.resolve()
      : new Promise((r) => existing.addEventListener('load', () => r(), { once: true }));
  }
  const link = document.createElement('link');
  link.id = LEAFLET_CSS_ID;
  link.rel = 'stylesheet';
  link.href = 'leaflet.css';
  const loaded = new Promise<void>((resolve) => {
    link.addEventListener('load', () => resolve(), { once: true });
    link.addEventListener('error', () => resolve(), { once: true });
  });
  document.head.appendChild(link);
  return loaded;
}

function cssVar(name: string, fallback: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
}

/** A run route on OpenStreetMap tiles. Start and finish are circles (no image assets). */
@Component({
  selector: 'app-route-map',
  template: '<div #map class="map" role="img" aria-label="Route map"></div>',
  styles: `
    .map {
      /* Keep Leaflet's high z-index panes below the app's top bar and bottom nav. */
      position: relative;
      z-index: 0;
      isolation: isolate;
      height: 300px;
      border-radius: 16px;
      overflow: hidden;
      background: var(--mat-sys-surface-container);
    }
    :host ::ng-deep .leaflet-tile-pane {
      filter: saturate(1.05);
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RouteMapComponent implements OnDestroy {
  readonly track = input.required<TrackPointOut[]>();

  private readonly el = viewChild.required<ElementRef<HTMLDivElement>>('map');
  private map: L.Map | null = null;
  private destroyed = false;

  constructor() {
    afterRenderEffect(() => {
      const track = this.track();
      void ensureLeafletCss().then(() => this.draw(track));
    });
  }

  ngOnDestroy(): void {
    this.destroyed = true;
    this.map?.remove();
  }

  private draw(track: TrackPointOut[]): void {
    if (this.destroyed) return;
    this.map?.remove();
    this.map = null;
    if (track.length < 2) return;
    const latlngs = track.map((p) => L.latLng(p.lat, p.lng));
    const map = L.map(this.el().nativeElement, { scrollWheelZoom: false });
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors',
    }).addTo(map);

    const primary = cssVar('--mat-sys-primary', '#ffb59d');
    const surface = cssVar('--mat-sys-surface', '#1c1b1f');
    const line = L.polyline(latlngs, { color: primary, weight: 4, opacity: 0.95 }).addTo(map);
    L.circleMarker(latlngs[0], {
      radius: 7,
      color: surface,
      weight: 2,
      fillColor: '#4caf50',
      fillOpacity: 1,
    })
      .bindTooltip('Start')
      .addTo(map);
    L.circleMarker(latlngs[latlngs.length - 1], {
      radius: 7,
      color: surface,
      weight: 2,
      fillColor: primary,
      fillOpacity: 1,
    })
      .bindTooltip('Finish')
      .addTo(map);
    map.fitBounds(line.getBounds(), { padding: [24, 24] });
    this.map = map;
  }
}
