import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import Navbar from '../components/layout/Navbar';
import { CitizenSidebar, DashboardLayout, OfficerSidebar } from '../components/layout/Sidebar';
import IncidentMap from '../components/maps/IncidentMap';
import { incidentAPI } from '../services/api';
import { CATEGORIES } from '../utils/helpers';

const DEFAULT_CENTER = [18.5204, 73.8567];
const PRIORITIES = ['High', 'Critical', 'Medium', 'Low'];
const STATUSES = ['Submitted', 'Under Review', 'Assigned', 'In Progress', 'Resolved', 'Closed', 'Reopened'];

function dateRangeStart(range) {
  if (range === 'all') return undefined;
  const start = new Date();
  start.setDate(start.getDate() - Number(range));
  return start.toISOString();
}

function FilterSelect({ label, value, onChange, options }) {
  return (
    <label className="flex min-w-36 flex-col gap-1 text-xs font-medium text-slate-600">
      {label}
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800"
      >
        {options.map(([optionValue, optionLabel]) => (
          <option key={optionValue} value={optionValue}>{optionLabel}</option>
        ))}
      </select>
    </label>
  );
}

function MapContent({ audience }) {
  const [filters, setFilters] = useState({
    category: '',
    priority: '',
    status: '',
    jurisdiction_id: '',
    radius_km: '10',
    date_range: 'all',
  });
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const requestParams = useMemo(() => {
    const params = {
      category: filters.category,
      priority: filters.priority,
      status: filters.status,
      jurisdiction_id: filters.jurisdiction_id,
      radius_km: filters.radius_km,
      date_from: dateRangeStart(filters.date_range),
    };
    Object.keys(params).forEach((key) => {
      if (!params[key]) delete params[key];
    });
    return params;
  }, [filters]);

  useEffect(() => {
    let active = true;
    incidentAPI.mapData(requestParams)
      .then((response) => {
        if (!active) return;
        setData(response.data);
        if (!filters.jurisdiction_id && response.data.jurisdictions?.length) {
          setLoading(true);
          const defaultJurisdiction = response.data.jurisdictions.find(
            (jurisdiction) => jurisdiction.name.toLowerCase() === 'pune central',
          ) || response.data.jurisdictions[0];
          setFilters((current) => (
            current.jurisdiction_id
              ? current
              : { ...current, jurisdiction_id: defaultJurisdiction.id }
          ));
        }
      })
      .catch((requestError) => {
        if (active) {
          setError(requestError.response?.data?.detail || 'Could not load map data. Please try again.');
          setData(null);
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [filters.jurisdiction_id, requestParams]);

  const center = useMemo(() => (
    data?.center
      ? [data.center.latitude, data.center.longitude]
      : DEFAULT_CENTER
  ), [data]);
  const setFilter = (key) => (value) => setFilters((current) => ({ ...current, [key]: value }));
  const applyFilter = (key) => (value) => {
    setLoading(true);
    setError('');
    setFilter(key)(value);
  };
  const page = (
    <div className="mx-auto max-w-7xl space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="mb-1 text-xs font-semibold uppercase tracking-[0.16em] text-teal-700">Civic intelligence</p>
          <h1 className="text-3xl font-semibold text-[#1e3a5f]">Geographic issue map</h1>
          <p className="mt-1 text-sm text-slate-600">Explore real report locations and their linked incidents.</p>
        </div>
        {audience !== 'public' && (
          <Link to={audience === 'officer' ? '/officer/incidents' : '/nearby'} className="text-sm font-medium text-teal-700 hover:underline">
            {audience === 'officer' ? 'Open incident queue' : 'Nearby issues'}
          </Link>
        )}
      </header>

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-label="Map data totals">
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <p className="text-sm text-slate-500">Citizen reports on map</p>
          <p className="mt-1 text-2xl font-semibold text-[#1e3a5f]">{data?.total_reports ?? '—'}</p>
          <p className="text-xs text-slate-500">Each geocoded report counted once</p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <p className="text-sm text-slate-500">Distinct linked incidents</p>
          <p className="mt-1 text-2xl font-semibold text-[#1e3a5f]">{data?.distinct_incidents ?? '—'}</p>
          <p className="text-xs text-slate-500">Unique incident IDs among filtered reports</p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <p className="text-sm text-slate-500">Reports without coordinates</p>
          <p className="mt-1 text-2xl font-semibold text-[#1e3a5f]">{data?.unmapped_reports ?? '—'}</p>
          <p className="text-xs text-slate-500">Excluded from map and density</p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <p className="text-sm text-slate-500">Showing jurisdiction</p>
          <p className="mt-1 truncate text-lg font-semibold text-[#1e3a5f]">
            {data?.jurisdictions?.find((item) => item.id === filters.jurisdiction_id)?.name || 'Pune Central'}
          </p>
          <p className="text-xs text-slate-500">Map position uses stored jurisdiction coordinates</p>
        </div>
      </section>

      <section className="flex flex-wrap items-end gap-3 rounded-lg border border-slate-200 bg-white p-4" aria-label="Map filters">
        <FilterSelect
          label="Jurisdiction"
          value={filters.jurisdiction_id}
          onChange={applyFilter('jurisdiction_id')}
          options={[
            ['', data?.jurisdictions?.length ? 'Select jurisdiction' : 'No jurisdictions found'],
            ...(data?.jurisdictions || []).map((item) => [item.id, item.name]),
          ]}
        />
        <FilterSelect label="Category" value={filters.category} onChange={applyFilter('category')} options={[
          ['', 'All categories'],
          ...CATEGORIES.map((value) => [value, value]),
        ]} />
        <FilterSelect label="Priority" value={filters.priority} onChange={applyFilter('priority')} options={[
          ['', 'All priorities'],
          ...PRIORITIES.map((value) => [value, value]),
        ]} />
        <FilterSelect label="Report status" value={filters.status} onChange={applyFilter('status')} options={[
          ['', 'All statuses'],
          ...STATUSES.map((value) => [value, value]),
        ]} />
        <FilterSelect label="Radius" value={filters.radius_km} onChange={applyFilter('radius_km')} options={[
          ['1', '1 km'], ['2', '2 km'], ['5', '5 km'], ['10', '10 km'], ['25', '25 km'], ['50', '50 km'],
        ]} />
        <FilterSelect label="Date range" value={filters.date_range} onChange={applyFilter('date_range')} options={[
          ['all', 'Any time'], ['7', 'Last 7 days'], ['30', 'Last 30 days'], ['90', 'Last 90 days'],
        ]} />
        <button
          type="button"
          onClick={() => {
            setLoading(true);
            setError('');
            setFilters({
              category: '',
              priority: '',
              status: '',
              jurisdiction_id: data?.jurisdictions?.[0]?.id || '',
              radius_km: '10',
              date_range: 'all',
            });
          }}
          className="rounded-md px-3 py-2 text-sm font-medium text-teal-700 hover:bg-teal-50"
        >
          Reset filters
        </button>
      </section>

      {error && <p role="alert" className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p>}
      {loading && <p role="status" className="text-sm text-slate-500">Updating map data…</p>}

      <IncidentMap
        reports={data?.reports || []}
        incidents={data?.incidents || []}
        center={center}
        heightClass="h-[min(70vh,720px)]"
        linkPrefix={audience === 'public' ? '/explore/incidents' : '/incidents'}
      />

      <div className="flex flex-wrap items-center gap-x-5 gap-y-2 rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-600">
        <span className="font-semibold text-slate-800">Priority colors:</span>
        {[
          ['#dc2626', 'High / Critical'],
          ['#f59e0b', 'Medium'],
          ['#0d9488', 'Low'],
          ['#64748b', 'Not assigned'],
        ].map(([color, label]) => (
          <span key={label} className="inline-flex items-center gap-2">
            <span className="h-3 w-3 rounded-full" style={{ backgroundColor: color }} />
            {label}
          </span>
        ))}
        <p className="basis-full border-t border-slate-100 pt-2 text-xs text-slate-500">
          Cluster numbers are counts of reports (or distinct incidents when selected). Cluster color is the highest priority represented: High/Critical overrides Medium, then Low; unassigned-only groups are slate. Heat-map intensity counts each report once; heat-map colors show density, not priority.
        </p>
      </div>

      <section className="overflow-hidden rounded-lg border border-slate-200 bg-white">
        <div className="border-b border-slate-100 px-4 py-3">
          <h2 className="font-semibold text-[#1e3a5f]">Reports in the selected area</h2>
        </div>
        {!data?.reports?.length ? (
          <p className="p-4 text-sm text-slate-500">No reports with usable coordinates match these filters.</p>
        ) : (
          <ul className="divide-y divide-slate-100">
            {data.reports.slice(0, 8).map((report) => (
              <li key={report.id} className="flex flex-wrap items-center justify-between gap-2 px-4 py-3">
                <div>
                  <p className="font-medium text-slate-800">{report.title}</p>
                  <p className="text-xs text-slate-500">{report.category} · {report.status} · {report.priority || 'Priority not assigned'}</p>
                </div>
                {report.incident_id ? (
                <Link
                  to={`${audience === 'public' ? '/explore/incidents' : '/incidents'}/${report.incident_id}`}
                  className="text-xs text-teal-700 hover:underline"
                >
                  {report.incident_number || report.incident_id}
                </Link>
                ) : (
                <p className="text-xs text-slate-500">Unlinked report · {report.id}</p>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );

  if (audience === 'citizen') {
    return <><Navbar /><DashboardLayout sidebar={<CitizenSidebar />}>{page}</DashboardLayout></>;
  }
  if (audience === 'officer') {
    return <><Navbar /><DashboardLayout sidebar={<OfficerSidebar />}>{page}</DashboardLayout></>;
  }
  return <div className="min-h-screen bg-gray-50"><Navbar /><main className="px-4 py-8">{page}</main></div>;
}

export default function CivicMapPage({ audience = 'public' }) {
  return <MapContent audience={audience} />;
}
