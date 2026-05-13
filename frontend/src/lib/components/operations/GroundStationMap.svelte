<script lang="ts">
  import { onMount, onDestroy, untrack } from 'svelte';
  import 'leaflet/dist/leaflet.css';

  type StationLocation = {
    id?: string;
    label: string;
    lat: number;
    lon: number;
    elevationM: number;
  };

  type TrackPoint = {
    lat: number;
    lon: number;
    elevation?: number;
    time?: string | Date;
  };

  let {
    location,
    presets = [],
    selectedTrack = [],
    onLocationChange,
  } = $props<{
    location: StationLocation;
    presets?: StationLocation[];
    selectedTrack?: TrackPoint[];
    onLocationChange?: (location: StationLocation) => void;
  }>();

  let mapContainer: HTMLElement;
  let map = $state<import('leaflet').Map | null>(null);
  let L = $state<typeof import('leaflet') | null>(null);
  let trackLayer: import('leaflet').Polyline | null = null;
  let currentMarker: import('leaflet').Marker | null = null;
  let presetMarkers: import('leaflet').Marker[] = [];

  function roundCoord(value: number) {
    return Math.round(value * 10000) / 10000;
  }

  $effect(() => {
    if (map && L) {
      const lat = location.lat;
      const lon = location.lon;
      
      untrack(() => {
        if (currentMarker) {
          const latlng = L!.latLng(lat, lon);
          currentMarker.setLatLng(latlng);
          map!.setView(latlng, map!.getZoom(), { animate: true });
        }
      });
    }
  });

  $effect(() => {
    if (map && L) {
      const track = selectedTrack;
      
      untrack(() => {
        if (trackLayer) {
          trackLayer.remove();
          trackLayer = null;
        }
        if (track && track.length > 0) {
          const latlngs = track.map((p: TrackPoint) => L!.latLng(p.lat, p.lon));
          trackLayer = L!.polyline(latlngs, { color: '#b12142', weight: 3, dashArray: '5, 5' }).addTo(map!);
        }
      });
    }
  });

  onMount(async () => {
    const leaflet = await import('leaflet');
    L = leaflet;
    
    // Fix leaflet marker icon paths since they might not load correctly with Vite
    delete (L.Icon.Default.prototype as any)._getIconUrl;
    L.Icon.Default.mergeOptions({
      iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
      iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
      shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png'
    });

    const m = L.map(mapContainer, {
      center: [location.lat, location.lon],
      zoom: 2,
      worldCopyJump: true
    });

    // Cleaner map tiles - CartoDB Voyager (lighter but clean)
    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      subdomains: 'abcd',
      maxZoom: 20
    }).addTo(m);

    currentMarker = L.marker([location.lat, location.lon], { zIndexOffset: 1000 }).addTo(m);
    
    map = m;

    map.on('click', (e) => {
      onLocationChange?.({
        id: 'custom',
        label: 'Custom Ground Station',
        lat: roundCoord(e.latlng.lat),
        lon: roundCoord(e.latlng.lng),
        elevationM: location.elevationM,
      });
    });

    // Preset markers
    presets.forEach((preset: StationLocation) => {
      const presetIcon = L!.divIcon({
        className: 'custom-div-icon',
        html: `<div style="background-color: var(--color-ink-3); width: 12px; height: 12px; border-radius: 50%; border: 2px solid var(--color-panel);"></div>`,
        iconSize: [12, 12],
        iconAnchor: [6, 6]
      });

      const marker = L!.marker([preset.lat, preset.lon], { icon: presetIcon })
        .addTo(map!)
        .bindTooltip(preset.label);
      
      marker.on('click', (e) => {
        L!.DomEvent.stopPropagation(e);
        onLocationChange?.({
          ...preset,
          lat: roundCoord(preset.lat),
          lon: roundCoord(preset.lon),
          elevationM: Number.isFinite(preset.elevationM) ? preset.elevationM : 0,
        });
      });
      presetMarkers.push(marker);
    });
  });

  onDestroy(() => {
    if (map) {
      map.remove();
      map = null;
    }
  });
</script>

<div class="space-y-3">
  <div class="overflow-hidden rounded-2xl border border-border bg-surface/60 p-[1px]">
    <div bind:this={mapContainer} class="h-[360px] w-full rounded-[15px] z-0"></div>
  </div>

  <div class="flex flex-wrap items-center justify-between gap-3 text-xs text-ink-3">
    <span class="font-medium text-ink-2">{location.label}</span>
    <span class="font-mono">
      {location.lat.toFixed(4)} lat, {location.lon.toFixed(4)} lon, {Math.round(location.elevationM)} m
    </span>
  </div>
</div>

<style>
  /* To ensure leaflet container has proper z-index and doesn't overlap sidebar/modals */
  :global(.leaflet-container) {
    z-index: 10;
    font-family: inherit;
    background: transparent;
  }
  :global(.leaflet-control-container) {
    z-index: 20;
  }
</style>
