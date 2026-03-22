import { useState } from "react";
import PropTypes from "prop-types";
import AnalyticsCommandCenter from "./AnalyticsCommandCenter";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:5000";

function MayorDashboard({ data, authToken }) {
  const [drillDownData, setDrillDownData] = useState(null);
  const [loading, setLoading] = useState(false);

  if (!data || !data.analytics) {
    return (
      <section className="card">
        <h3>Mayor's Analytics Command Center</h3>
        <p>Loading city-wide telemetry...</p>
      </section>
    );
  }

  const handleDrillDown = async (filters) => {
    setLoading(true);
    setDrillDownData({ filters, tickets: [] }); // Open modal immediately with loading state
    try {
      // Build query string e.g. ?ward=Ward-1&status=Open
      const queryParams = new URLSearchParams(filters);
      // For Mayor Drill-Downs typically we only want unresolved unless specified
      if (!filters.status && !filters.department) queryParams.append("status", "Escalated");

      const response = await fetch(`${API_BASE}/api/search?${queryParams.toString()}&limit=20`, {
        headers: { Authorization: `Bearer ${authToken}` }
      });
      if (response.ok) {
        const payload = await response.json();
        setDrillDownData({ filters, tickets: payload.results });
      } else {
        setDrillDownData(null);
      }
    } catch {
      setDrillDownData(null);
    } finally {
      setLoading(false);
    }
  };

  const closeDrillDown = () => setDrillDownData(null);

  return (
    <section className="stack mayor-stack">
      <section className="card" style={{ paddingBottom: '0.5rem' }}>
        <h3>Mayor's Analytics Command Center</h3>
        <p>Real-time city-wide telemetry across all governance tiers.</p>
        <div className="kpi-grid admin-kpi-grid" style={{ marginTop: '1.5rem' }}>
          <Kpi label="Total Registered Tickets" value={data.summary.total_complaints} customColor="var(--text)" />
          <Kpi label="Active Investigations" value={data.summary.open_complaints} customColor="var(--accent)" />
          <Kpi label="Successfully Resolved" value={data.summary.resolved_complaints} customColor="var(--green)" />
          <Kpi label="Critically Escalated" value={data.summary.escalated_complaints} customColor="orange" />
        </div>
      </section>

      {/* Render the new Recharts Command Center */}
      <AnalyticsCommandCenter analytics={data.analytics} onDrillDown={handleDrillDown} />

      {/* Drill-Down Modal */}
      {drillDownData && (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && closeDrillDown()}>
          <div className="modal-content" style={{ maxWidth: '600px', width: '100%' }}>
            <div className="modal-header">
              <h3>
                Drill-Down Analysis
                <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)', marginLeft: '1rem' }}>
                  {Object.entries(drillDownData.filters).map(([k, v]) => `${k}:${v}`).join(' | ')}
                </span>
              </h3>
              <button type="button" className="modal-close" onClick={closeDrillDown}>✕</button>
            </div>
            <div className="modal-body" style={{ maxHeight: '60vh', overflowY: 'auto' }}>
              {loading && <p>Fetching live records...</p>}
              {!loading && drillDownData.tickets.length === 0 && <p className="helper-text">No active records matched this query.</p>}
              {!loading && drillDownData.tickets.length > 0 && (
                <div className="manager-list">
                  {drillDownData.tickets.map(ticket => (
                    <div key={ticket.ticket_id} className="manager-item" style={{ flexDirection: 'column', alignItems: 'flex-start' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%', marginBottom: '0.3rem' }}>
                        <strong style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          {ticket.ticket_id}
                          <span className={`badge tier-${ticket.current_tier?.toLowerCase() || 'local'}`}>{ticket.current_tier || 'Local'}</span>
                        </strong>
                        <span className="badge secondary">{ticket.status}</span>
                      </div>
                      <p className="helper-text">{ticket.department} &bull; Ward: {ticket.ward}</p>
                      <p style={{ marginTop: '0.5rem', fontSize: '0.9rem' }}>{ticket.description}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

function Kpi({ label, value, customColor }) {
  return (
    <article className="kpi-card" style={customColor ? { borderBottom: `4px solid ${customColor}` } : {}}>
      <p style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>{label}</p>
      <h4 style={{ color: customColor || "inherit", margin: "0.3rem 0" }}>{value}</h4>
    </article>
  );
}

Kpi.propTypes = {
  label: PropTypes.string.isRequired,
  value: PropTypes.number.isRequired,
  customColor: PropTypes.string
};

MayorDashboard.propTypes = {
  data: PropTypes.shape({
    summary: PropTypes.shape({
      total_complaints: PropTypes.number.isRequired,
      open_complaints: PropTypes.number.isRequired,
      resolved_complaints: PropTypes.number.isRequired,
      escalated_complaints: PropTypes.number.isRequired
    }),
    analytics: PropTypes.object
  }),
  authToken: PropTypes.string.isRequired
};

MayorDashboard.defaultProps = {
  data: null
};

export default MayorDashboard;