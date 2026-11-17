import { useEffect, useMemo, useState } from 'react';
import {
  CircleMarker,
  MapContainer,
  Popup,
  TileLayer,
  Tooltip,
  useMap,
  useMapEvents,
} from 'react-leaflet';
import { Link } from 'react-router-dom';
import L from 'leaflet';

const PRIORITY_COLORS = {
  critical: '#dc2626',
  high: '#dc2626',
  medium: '#f59e0b',
  low: '#0d9488',
  unknown: '#64748b',
};

function priorityColor(priority) {
  return PRIORITY_COLORS[String(priority || '').toLowerCase()] || PRIORITY_COLORS.unknown;
}

function priorityRank(priority) {
  const value = String(priority || '').toLowerCase();
  if (value === 'critical' || value === 'high') return 3;
  if (value === 'medium') return 2;
  if (value === 'low') return 1;
  return 0;
}

function groupNearbyItems(items, map, radius = 48) {
  const buckets = new Map();
  const cellSize = radius;
  const groups = [];

  items.forEach((item) => {
    const latitude = Number(item.latitude ?? item.center_latitude);
    const longitude = Number(item.longitude ?? item.center_longitude);
    const point = map.latLngToContainerPoint([latitude, longitude]);
    const cellX = Math.floor(point.x / cellSize);
    const cellY = Math.floor(point.y / cellSize);
    let group;

    for (let x = cellX - 1; x <= cellX + 1 && !group; x += 1) {
      for (let y = cellY - 1; y <= cellY + 1 && !group; y += 1) {
        const nearbyGroups = buckets.get(`${x}:${y}`) || [];
        group = nearbyGroups.find((candidate) => (
          candidate.center.distanceTo(point) <= radius
        ));
      }
    }

    if (!group) {
      group = { center: point, items: [] };
      groups.push(group);
      const key = `${cellX}:${cellY}`;
      buckets.set(key, [...(buckets.get(key) || []), group]);
    }

    group.items.push(item);
    group.center = L.point(
      group.center.x + (point.x - group.center.x) / group.items.length,
      group.center.y + (point.y - group.center.y) / group.items.length,
    );
  });

  return groups.map((group) => ({
    ...group,
    position: map.containerPointToLatLng(group.center),
    priority: group.items.reduce((highest, item) => {
      const itemPriority = item.priority ?? item.approved_priority ?? item.recommended_priority;
      return priorityRank(itemPriority) > priorityRank(highest) ? itemPriority : highest;
    }, null) || 'unknown',
  }));
}

function MapController({ center, zoom }) {
  const map = useMap();
  const latitude = Number(center[0]);
  const longitude = Number(center[1]);

  useEffect(() => {
    if (
      Number.isFinite(latitude) && Number.isFinite(longitude)
      && latitude >= -90 && latitude <= 90
      && longitude >= -180 && longitude <= 180
    ) {
      map.setView([latitude, longitude], zoom);
    }
  }, [latitude, longitude, map, zoom]);

  return null;
}

function ViewportUpdater({ onChange }) {
  const map = useMapEvents({
    moveend: () => onChange((value) => value + 1),
    zoomend: () => onChange((value) => value + 1),
  });

  useEffect(() => {
    const container = map.getContainer();
    let lastWidth = container.clientWidth;
    let lastHeight = container.clientHeight;
    const observer = new ResizeObserver(([entry]) => {
      const { width, height } = entry.contentRect;
      if (width === lastWidth && height === lastHeight) return;

      lastWidth = width;
      lastHeight = height;
      map.invalidateSize();
      onChange((value) => value + 1);
    });
    observer.observe(container);
    map.invalidateSize();
    return () => observer.disconnect();
  }, [map, onChange]);

  return null;
}

function DensityLayer({ items }) {
  const map = useMap();

  useEffect(() => {
    const canvas = document.createElement('canvas');
    canvas.setAttribute('aria-hidden', 'true');
    Object.assign(canvas.style, {
      position: 'absolute',
      inset: '0',
      width: '100%',
      height: '100%',
      pointerEvents: 'none',
      zIndex: '350',
    });
    map.getContainer().appendChild(canvas);

    const draw = () => {
      const size = map.getSize();
      const ratio = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.max(1, Math.round(size.x * ratio));
      canvas.height = Math.max(1, Math.round(size.y * ratio));
      const context = canvas.getContext('2d');
      if (!context) return;

      context.setTransform(ratio, 0, 0, ratio, 0, 0);
      context.clearRect(0, 0, size.x, size.y);
      context.globalCompositeOperation = 'lighter';
      const radius = 26;

      items.forEach((item) => {
        const point = map.latLngToContainerPoint([
          Number(item.latitude ?? item.center_latitude),
          Number(item.longitude ?? item.center_longitude),
        ]);
        if (
          point.x < -radius || point.y < -radius
          || point.x > size.x + radius || point.y > size.y + radius
        ) return;

        const gradient = context.createRadialGradient(
          point.x, point.y, 0, point.x, point.y, radius,
        );
        gradient.addColorStop(0, 'rgba(220, 38, 38, 0.28)');
        gradient.addColorStop(0.35, 'rgba(245, 158, 11, 0.19)');
        gradient.addColorStop(1, 'rgba(13, 148, 136, 0)');
        context.fillStyle = gradient;
        context.fillRect(point.x - radius, point.y - radius, radius * 2, radius * 2);
      });

      context.globalCompositeOperation = 'source-over';
    };

    draw();
    map.on('moveend zoomend resize', draw);
    return () => {
      map.off('moveend zoomend resize', draw);
      canvas.remove();
    };
  }, [items, map]);

  return null;
}

function MarkerPopup({ item, isIncident, linkPrefix }) {
  const targetIncidentId = isIncident ? item.id : item.incident_id;
  const priority = item.priority ?? item.approved_priority ?? item.recommended_priority;

  return (
    <div className="min-w-44 space-y-1 text-sm">
      <p className="font-semibold text-[#1e3a5f]">{item.title || (isIncident ? 'Civic incident' : 'Civic report')}</p>
      <p>Category: {item.category || '—'}</p>
      <p>Priority: {priority || 'Not assigned'}</p>
      <p>Status: {item.status || 'Unknown'}</p>
      <p>{isIncident ? 'Incident ID' : 'Report ID'}: {item.id}</p>
      {!isIncident && item.incident_id && <p>Linked incident ID: {item.incident_id}</p>}
      {isIncident && <p>Reports in current filters: {item.complaint_count ?? 0}</p>}
      {targetIncidentId && linkPrefix && (
        <Link
          to={`${linkPrefix}/${encodeURIComponent(targetIncidentId)}`}
          className="inline-block pt-1 font-medium text-teal-700 hover:underline"
        >
          View incident details
        </Link>
      )}
    </div>
  );
}

function ItemMarker({ item, isIncident, linkPrefix, clustered = false }) {
  const priority = item.priority ?? item.approved_priority ?? item.recommended_priority;
  const color = priorityColor(priority);

  return (
    <CircleMarker
      center={[Number(item.latitude ?? item.center_latitude), Number(item.longitude ?? item.center_longitude)]}
      radius={clustered ? 8 : 7}
      pathOptions={{ color: '#ffffff', weight: 2, fillColor: color, fillOpacity: 0.95 }}
    >
      {clustered && <Tooltip permanent direction="center" className="civic-cluster-count">1</Tooltip>}
      <Popup>
        <MarkerPopup item={item} isIncident={isIncident} linkPrefix={linkPrefix} />
      </Popup>
    </CircleMarker>
  );
}

function NumberedCluster({ group, isIncident, linkPrefix }) {
  const map = useMap();
  const color = priorityColor(group.priority);
  const count = group.items.length;

  const handleClick = () => {
    if (count < 2) return;
    map.setView(
      group.position,
      Math.min(map.getZoom() + 2, map.getMaxZoom() || 19),
      { animate: true },
    );
  };

  return (
    <CircleMarker
      center={group.position}
      radius={Math.min(34, 17 + Math.log2(count) * 4)}
      pathOptions={{ color: '#ffffff', weight: 3, fillColor: color, fillOpacity: 0.96 }}
      eventHandlers={{ click: handleClick }}
    >
      <Tooltip permanent direction="center" className="civic-cluster-count">{count}</Tooltip>
      <Popup>
        <div className="min-w-48 space-y-2 text-sm">
          <p className="font-semibold text-[#1e3a5f]">
            {count} {isIncident ? 'incidents' : 'reports'} in this area
          </p>
          {count > 1 && <p className="text-xs text-slate-500">Zoom in to separate these locations.</p>}
          <ul className="max-h-48 space-y-2 overflow-y-auto">
            {group.items.map((item) => (
              <li key={item.id}>
                <p className="font-medium">{item.title || (isIncident ? 'Civic incident' : 'Civic report')}</p>
                <p className="text-xs text-slate-500">{item.category || '—'} · {item.status || 'Unknown'}</p>
                <MarkerPopup item={item} isIncident={isIncident} linkPrefix={linkPrefix} />
              </li>
            ))}
          </ul>
        </div>
      </Popup>
    </CircleMarker>
  );
}

function ClusterLayer({ items, isIncident, linkPrefix }) {
  const map = useMap();
  const groups = groupNearbyItems(items, map, 48);

  return groups.map((group) => (
    <NumberedCluster
      key={group.items.map((item) => item.id).join(':')}
      group={group}
      isIncident={isIncident}
      linkPrefix={linkPrefix}
    />
  ));
}

export default function IncidentMap({
  reports,
  incidents = [],
  center = [18.5204, 73.8567],
  zoom = 13,
  heightClass = 'h-96',
  linkPrefix,
}) {
  const [mode, setMode] = useState('clusters');
  const [pointType, setPointType] = useState(reports === undefined ? 'incidents' : 'reports');
  const [viewportRevision, setViewportRevision] = useState(0);
  const hasReports = reports !== undefined;
  const isIncident = pointType === 'incidents' || !hasReports;
  const items = useMemo(() => {
    const source = isIncident ? incidents : reports;
    return (source || []).filter((item) => {
      const latitude = Number(item.latitude ?? item.center_latitude);
      const longitude = Number(item.longitude ?? item.center_longitude);
      return Number.isFinite(latitude) && Number.isFinite(longitude)
        && latitude >= -90 && latitude <= 90
        && longitude >= -180 && longitude <= 180
        && !(latitude === 0 && longitude === 0);
    });
  }, [incidents, isIncident, reports]);

  return (
    <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 p-3">
        <div className="flex flex-wrap gap-1" aria-label="Map visualization mode">
          {[
            ['clusters', 'Clusters'],
            ['heatmap', 'Heat map'],
            ['markers', 'Individual markers'],
          ].map(([value, label]) => (
            <button
              key={value}
              type="button"
              onClick={() => setMode(value)}
              aria-pressed={mode === value}
              className={`rounded-md px-3 py-2 text-sm font-medium ${
                mode === value ? 'bg-[#1e3a5f] text-white' : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        {hasReports && (
          <div className="flex gap-1" aria-label="Map point type">
            {[
              ['reports', 'Citizen reports'],
              ['incidents', 'Distinct incidents'],
            ].map(([value, label]) => (
              <button
                key={value}
                type="button"
                onClick={() => setPointType(value)}
                aria-pressed={pointType === value}
                className={`rounded-md border px-3 py-2 text-sm ${
                  pointType === value ? 'border-teal-600 bg-teal-50 text-teal-800' : 'border-slate-200 text-slate-600'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        )}
      </div>
      <div className={`relative ${heightClass}`}>
        <MapContainer
          center={[Number(center[0]), Number(center[1])]}
          zoom={zoom}
          scrollWheelZoom
          zoomControl
          className="h-full w-full"
        >
          <MapController center={center} zoom={zoom} />
          <ViewportUpdater onChange={setViewportRevision} />
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>'
            url="https://tile.openstreetmap.de/{z}/{x}/{y}.png"
            maxZoom={19}
          />
          {mode === 'heatmap' && <DensityLayer items={items} />}
          {mode === 'markers' && items.map((item) => (
            <ItemMarker
              key={item.id}
              item={item}
              isIncident={isIncident}
              linkPrefix={linkPrefix}
            />
          ))}
          {mode === 'clusters' && (
            <ClusterLayer
              items={items}
              isIncident={isIncident}
              linkPrefix={linkPrefix}
            />
          )}
        </MapContainer>
        {items.length === 0 && (
          <div className="pointer-events-none absolute left-1/2 top-4 z-[1000] -translate-x-1/2 rounded-md bg-white/95 px-4 py-2 text-sm text-slate-600 shadow">
            No locations match the selected filters.
          </div>
        )}
      </div>
      <span className="sr-only" aria-live="polite">{viewportRevision ? 'Map view updated' : ''}</span>
    </section>
  );
}
