'use client';

import type { DeviceType } from '@/types/app-builder';

interface DevicePreviewFrameProps {
  htmlUrl: string | null;
  device: DeviceType;
  onDeviceChange: (device: DeviceType) => void;
  isGeneratingDevice?: boolean;
}

const DEVICE_DIMS: Record<DeviceType, number> = {
  DESKTOP: 1280,
  TABLET: 768,
  MOBILE: 390,
};

const DEVICE_LABELS: Array<{ key: DeviceType; label: string }> = [
  { key: 'DESKTOP', label: 'Desktop' },
  { key: 'MOBILE', label: 'Mobile' },
  { key: 'TABLET', label: 'Tablet' },
];

/**
 * Sandboxed iframe with a device tab switcher (Desktop / Mobile / Tablet).
 * Switching to a device that has no cached variant triggers on-demand generation
 * via the onDeviceChange callback.
 */
export default function DevicePreviewFrame({
  htmlUrl,
  device,
  onDeviceChange,
  isGeneratingDevice = false,
}: DevicePreviewFrameProps) {
  return (
    <div className="flex flex-col gap-3">
      {/* Device tab switcher */}
      <div className="inline-flex rounded-lg bg-slate-100 p-1 self-center">
        {DEVICE_LABELS.map(({ key, label }) => {
          const isActive = device === key;
          return (
            <button
              key={key}
              type="button"
              onClick={() => onDeviceChange(key)}
              className={`rounded-md px-4 py-1.5 text-sm font-medium transition-all ${
                isActive
                  ? 'bg-white shadow-sm text-slate-900'
                  : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              {label}
            </button>
          );
        })}
      </div>

      {/* Preview area */}
      <div className="overflow-auto rounded-lg border border-slate-200 bg-slate-50">
        {htmlUrl ? (
          <div className="relative" style={{ height: '600px' }}>
            {isGeneratingDevice && (
              <div className="absolute inset-0 z-10 flex items-center justify-center bg-white/80 backdrop-blur-sm">
                <div className="flex flex-col items-center gap-2">
                  <div className="h-6 w-6 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
                  <span className="text-sm text-slate-600">
                    Generating {device.charAt(0) + device.slice(1).toLowerCase()} layout...
                  </span>
                </div>
              </div>
            )}
            <iframe
              key={htmlUrl}
              src={htmlUrl}
              title="Screen preview"
              sandbox="allow-scripts allow-same-origin"
              style={{
                width: `${DEVICE_DIMS[device]}px`,
                height: '600px',
                border: 'none',
                display: 'block',
              }}
            />
          </div>
        ) : (
          <div className="flex h-64 items-center justify-center text-slate-400">
            Select a variant to preview
          </div>
        )}
      </div>
    </div>
  );
}
