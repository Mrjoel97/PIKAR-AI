/**
 * IncidentPanel renders the list of open (unresolved) health incidents.
 * Shows endpoint, incident type badge, start time, and running duration.
 */

/** Incident shape from GET /admin/monitoring/status open_incidents field. */
export interface Incident {
  id: string;
  endpoint: string;
  category: string | null;
  incident_type: string;
  started_at: string;
  resolved_at: string | null;
  details: Record<string, unknown>;
  created_at: string;
}

/** Badge color per incident type */
const INCIDENT_BADGE: Record<string, string> = {
  down: 'bg-rose-900 text-rose-300',
  degraded: 'bg-amber-900 text-amber-300',
  latency_spike: 'bg-amber-900 text-amber-300',
  error_spike: 'bg-rose-900 text-rose-300',
};

function formatDuration(startedAt: string): string {
  const diffMs = Date.now() - new Date(startedAt).getTime();
  const totalSeconds = Math.floor(diffMs / 1000);
  if (totalSeconds < 60) return `${totalSeconds}s`;
  const minutes = Math.floor(totalSeconds / 60);
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return remainingMinutes > 0 ? `${hours}h ${remainingMinutes}m` : `${hours}h`;
}

interface IncidentPanelProps {
  incidents: Incident[];
}

export function IncidentPanel({ incidents }: IncidentPanelProps) {
  return (
    <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
      <h2 className="text-gray-100 font-semibold text-sm mb-4">Active Incidents</h2>

      {incidents.length === 0 ? (
        <div className="flex items-center gap-2 text-emerald-400 text-sm">
          <span className="text-lg">&#10003;</span>
          <span>No active incidents</span>
        </div>
      ) : (
        <ul className="flex flex-col gap-3">
          {incidents.map((incident) => {
            const badgeClass =
              INCIDENT_BADGE[incident.incident_type] ?? 'bg-gray-700 text-gray-400';
            const displayName =
              incident.endpoint.charAt(0).toUpperCase() + incident.endpoint.slice(1);
            const displayType = incident.incident_type.replace(/_/g, ' ');

            return (
              <li
                key={incident.id}
                className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-t border-gray-700 pt-3"
              >
                {/* Left: endpoint + type badge */}
                <div className="flex items-center gap-2 min-w-0">
                  <span className="text-gray-100 text-sm font-medium shrink-0">
                    {displayName}
                  </span>
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium capitalize ${badgeClass}`}
                  >
                    {displayType}
                  </span>
                </div>

                {/* Right: started_at + duration */}
                <div className="flex items-center gap-3 text-xs text-gray-400 shrink-0">
                  <span>
                    Started {new Date(incident.started_at).toLocaleString()}
                  </span>
                  <span className="text-gray-500">
                    ({formatDuration(incident.started_at)})
                  </span>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
