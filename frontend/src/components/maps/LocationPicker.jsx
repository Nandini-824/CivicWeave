import { useEffect, useState } from 'react';

import {
  MapContainer,
  TileLayer,
  Marker,
  useMap,
  useMapEvents,
} from 'react-leaflet';

import L from 'leaflet';

import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

// Fix default Leaflet marker icons
delete L.Icon.Default.prototype._getIconUrl;

L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});

const DEFAULT_CENTER = [18.5204, 73.8567];

// Move the map whenever the selected position changes
function MapController({ position, zoom = 16 }) {
  const map = useMap();

  useEffect(() => {
    if (position) {
      map.flyTo(position, zoom, {
        duration: 1.2,
      });
    }
  }, [position, zoom, map]);

  return null;
}

// Handle manual map clicks
function MapClickHandler({ onLocationSelect }) {
  useMapEvents({
    click(event) {
      onLocationSelect(
        event.latlng.lat,
        event.latlng.lng
      );
    },
  });

  return null;
}

export default function LocationPicker({
  latitude,
  longitude,
  onChange,
  address,
  onAddressChange,
  city,
  onCityChange,
}) {
  const hasCoordinates =
    latitude != null &&
    longitude != null &&
    Number.isFinite(Number(latitude)) &&
    Number.isFinite(Number(longitude));

  const [position, setPosition] = useState(
    hasCoordinates
      ? [Number(latitude), Number(longitude)]
      : DEFAULT_CENTER
  );

  const [pincode, setPincode] = useState('');
  const [searching, setSearching] = useState(false);
  const [message, setMessage] = useState('');

  // Keep the marker synchronized with the parent component
  useEffect(() => {
    if (hasCoordinates) {
      setPosition([
        Number(latitude),
        Number(longitude),
      ]);
    }
  }, [latitude, longitude, hasCoordinates]);

  // Select coordinates and update the parent form
  const handleSelect = (lat, lng) => {
    setPosition([lat, lng]);
    onChange(lat, lng);
    setMessage(
      `Location selected: ${lat.toFixed(5)}, ${lng.toFixed(5)}`
    );
  };

  // Fetch the user's current GPS location
  const useCurrentLocation = () => {
    setMessage('');

    if (!navigator.geolocation) {
      setMessage('Geolocation is not supported by your browser.');
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (result) => {
        const lat = result.coords.latitude;
        const lng = result.coords.longitude;

        handleSelect(lat, lng);
      },
      (error) => {
        if (error.code === error.PERMISSION_DENIED) {
          setMessage(
            'Location permission denied. Allow location access in your browser settings.'
          );
        } else {
          setMessage(
            'Could not fetch your location. Please search or select it on the map.'
          );
        }
      },
      {
        enableHighAccuracy: true,
        timeout: 15000,
        maximumAge: 0,
      }
    );
  };

  // Search for an address or PIN code
  const searchLocation = async () => {
  const cleanAddress = address?.trim();
  const cleanPincode = pincode.trim();
  const cleanCity = city?.trim() || 'Pune';

  if (!cleanAddress && !cleanPincode) {
    setMessage('Please enter an address or PIN code.');
    return;
  }

  setSearching(true);
  setMessage('');

  try {
    const searchQueries = [];

    // Search 1: Search by PIN code and city separately.
    if (cleanPincode) {
      const params = new URLSearchParams({
        postalcode: cleanPincode,
        city: cleanCity,
        state: 'Maharashtra',
        country: 'India',
        format: 'jsonv2',
        limit: '5',
        addressdetails: '1',
      });

      searchQueries.push(
        `https://nominatim.openstreetmap.org/search?${params}`
      );
    }

    // Search 2: Search by the address and city.
    if (cleanAddress) {
      const params = new URLSearchParams({
        q: `${cleanAddress}, ${cleanCity}, Maharashtra, India`,
        format: 'jsonv2',
        limit: '5',
        addressdetails: '1',
        countrycodes: 'in',
      });

      searchQueries.push(
        `https://nominatim.openstreetmap.org/search?${params}`
      );
    }

    // Try each search until a result is found.
    let result = null;

    for (const url of searchQueries) {
      const response = await fetch(url);

      if (!response.ok) {
        continue;
      }

      const results = await response.json();

      if (results.length > 0) {
        // Prefer a result matching the requested PIN code.
        result =
          results.find(
            (item) =>
              cleanPincode &&
              item.address?.postcode?.replace(/\s/g, '') ===
                cleanPincode
          ) || results[0];

        break;
      }
    }

    if (!result) {
      setMessage(
        'Location not found. Try a shorter address or check the PIN code.'
      );
      return;
    }

    const lat = Number(result.lat);
    const lng = Number(result.lon);

    if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
      setMessage('Invalid location coordinates. Please try again.');
      return;
    }

    // Update the selected coordinates and move the map.
    handleSelect(lat, lng);

    // Update the city if the result provides one.
    const detectedCity =
      result.address?.city ||
      result.address?.town ||
      result.address?.village ||
      result.address?.municipality;

    if (detectedCity) {
      onCityChange(detectedCity);
    }

    setMessage(
      'Location found! Zoom in and click the map to select the exact spot.'
    );
  } catch (error) {
    console.error('Location search error:', error);

    setMessage(
      'Search failed. Check your internet connection and try again.'
    );
  } finally {
    setSearching(false);
  }
};

  return (
    <div className="space-y-4">

      {/* Current location */}
      <div className="flex flex-wrap gap-2 items-center">
        <button
          type="button"
          onClick={useCurrentLocation}
          className="px-4 py-2 bg-teal-600 text-white rounded-md text-sm hover:bg-teal-700"
        >
          📍 Use Current Location
        </button>

        {hasCoordinates && (
          <span className="text-sm text-gray-600">
            {Number(latitude).toFixed(5)},
            {' '}
            {Number(longitude).toFixed(5)}
          </span>
        )}
      </div>

      {/* Address and PIN code search */}
      <div className="border border-gray-200 rounded-lg p-3 space-y-3">

        <h3 className="font-medium text-gray-800">
          Search for a location
        </h3>

        <input
          type="text"
          value={address}
          onChange={(event) =>
            onAddressChange(event.target.value)
          }
          placeholder="Enter street, landmark or area"
          className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
        />

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">

          <input
            type="text"
            value={pincode}
            onChange={(event) =>
              setPincode(
                event.target.value.replace(/\D/g, '').slice(0, 6)
              )
            }
            placeholder="Enter 6-digit PIN code"
            maxLength={6}
            inputMode="numeric"
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
          />

          <input
            type="text"
            value={city}
            onChange={(event) =>
              onCityChange(event.target.value)
            }
            placeholder="City"
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
          />

        </div>

        <button
          type="button"
          onClick={searchLocation}
          disabled={searching}
          className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700 disabled:opacity-50"
        >
          {searching ? 'Searching...' : '🔎 Find on Map'}
        </button>

      </div>

      {/* Interactive map */}
      <div className="h-72 rounded-lg overflow-hidden border border-gray-200">

        <MapContainer
          center={position}
          zoom={14}
          style={{
            height: '100%',
            width: '100%',
          }}
        >

          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>'
            url="https://tile.openstreetmap.de/{z}/{x}/{y}.png"
          />

          <MapController position={position} />

          <MapClickHandler
            onLocationSelect={handleSelect}
          />

          {/* Show marker at selected location */}
          {hasCoordinates && (
            <Marker
              position={[
                Number(latitude),
                Number(longitude),
              ]}
            />
          )}

        </MapContainer>

      </div>

      {/* Location status */}
      {message && (
        <p className="text-sm text-teal-700">
          {message}
        </p>
      )}

      <p className="text-sm text-gray-500">
        Search for an area or PIN code, then click the map
        to pinpoint the exact location of the issue.
      </p>

    </div>
  );
}