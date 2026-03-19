import { useState } from "react";
import PropTypes from "prop-types";
import AdminManagerModal from "./AdminManagerModal";

function RoleDashboard({ role, data, onStatusUpdate, authToken }) {
  const [activeManager, setActiveManager] = useState(null);
  const [selectedManager, setSelectedManager] = useState(null);

  if (!data) {
    return (
      <section className="card">
        <h3>Dashboard</h3>
        <p>Loading dashboard...</p>
      </section>
    );
  }

  if (role === "citizen") {
    return (
      <section className="card">
        <h3>Citizen Dashboard</h3>
        <div className="kpi-grid">
          <Kpi label="Total Complaints" value={data.summary.total_complaints} />
          <Kpi label="Open" value={data.summary.open_complaints} />
          <Kpi label="Resolved" value={data.summary.resolved_complaints} />
        </div>
        <h4>Recent Complaints</h4>
        <ul className="simple-list">
          {data.recent.map((item) => (
            <li key={item.ticket_id}>
              <strong>{item.ticket_id}</strong> - {item.department} - {item.status}
            </li>
          ))}
        </ul>
      </section>
    );
  }

  if (role === "officer") {
    return (
      <section className="card">
        <h3>Officer Dashboard ({data.ward})</h3>
        <div className="kpi-grid">
          <Kpi label="Assigned" value={data.summary.assigned} />
          <Kpi label="Pending" value={data.summary.pending} />
          <Kpi label="Resolved" value={data.summary.resolved} />
        </div>
        <h4>Action Queue</h4>
        <ul className="simple-list">
          {data.queue.map((item) => (
            <li key={item.ticket_id}>
              <div className="queue-row">
                <span>
                  <strong>{item.ticket_id}</strong> - {item.department} - {item.status}
                </span>
                <div className="button-row">
                  <button type="button" className="secondary" onClick={() => onStatusUpdate(item.ticket_id, "In Progress")}>In Progress</button>
                  <button type="button" onClick={() => onStatusUpdate(item.ticket_id, "Resolved")}>Resolve</button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      </section>
    );
  }

  return (
    <>
      <section className="card">
        <h3>Admin Dashboard</h3>
        <div className="kpi-grid">
          <Kpi label="Total Complaints" value={data.summary.total_complaints} />
          <Kpi label="Open" value={data.summary.total_open} />
          <Kpi label="Resolved" value={data.summary.total_resolved} />
          <Kpi label="Active Officers" value={data.summary.active_officers} />
          <Kpi label="Departments" value={data.summary.total_departments} />
          <Kpi label="Citizens" value={data.summary.registered_citizens} />
        </div>
      </section>

      <section className="card">
        <div className="manager-tabs" role="tablist" aria-label="Manager sections">
          <button
            type="button"
            className={`manager-tab ${selectedManager === "officers" ? "active" : ""}`}
            onClick={() => setSelectedManager("officers")}
          >
            Officer Manager
          </button>
          <button
            type="button"
            className={`manager-tab ${selectedManager === "departments" ? "active" : ""}`}
            onClick={() => setSelectedManager("departments")}
          >
            Department Manager
          </button>
          <button
            type="button"
            className={`manager-tab ${selectedManager === "citizens" ? "active" : ""}`}
            onClick={() => setSelectedManager("citizens")}
          >
            Citizen Manager
          </button>
        </div>
      </section>

      {!selectedManager && (
        <section className="card">
          <p className="empty-state">Click a manager name to view details.</p>
        </section>
      )}

      {selectedManager === "officers" && (
        <section className="card admin-manager-section">
          <div className="admin-manager-header">
            <h4>Officer Manager</h4>
            <button
              type="button"
              className="secondary"
              onClick={() => setActiveManager("officers")}
            >
              Manage
            </button>
          </div>
          <ul className="admin-list">
            {data.officer_manager?.length === 0 ? (
              <li className="empty-state">No officers. Click Manage to add.</li>
            ) : (
              data.officer_manager?.map((item) => (
                <li key={item.username} className="admin-list-item">
                  <strong>{item.display_name}</strong>
                  <span className="badge">{item.ward || "No ward assigned"}</span>
                  <span className="badge secondary">{item.assigned_complaints} complaints</span>
                </li>
              ))
            )}
          </ul>
        </section>
      )}

      {selectedManager === "departments" && (
        <section className="card admin-manager-section">
          <div className="admin-manager-header">
            <h4>Department Manager</h4>
            <button
              type="button"
              className="secondary"
              onClick={() => setActiveManager("departments")}
            >
              Manage
            </button>
          </div>
          <ul className="admin-list">
            {data.department_manager?.length === 0 ? (
              <li className="empty-state">No departments. Click Manage to add.</li>
            ) : (
              data.department_manager?.map((item) => (
                <li key={item.name} className="admin-list-item">
                  <strong>{item.name}</strong>
                  <span className="badge secondary">{item.complaints} complaints</span>
                </li>
              ))
            )}
          </ul>
        </section>
      )}

      {selectedManager === "citizens" && (
        <section className="card admin-manager-section">
          <div className="admin-manager-header">
            <h4>Citizen Manager</h4>
            <button
              type="button"
              className="secondary"
              onClick={() => setActiveManager("citizens")}
            >
              Manage
            </button>
          </div>
          <ul className="admin-list">
            {data.citizen_manager?.length === 0 ? (
              <li className="empty-state">No citizens. Click Manage to view.</li>
            ) : (
              data.citizen_manager?.map((item) => (
                <li key={item.mobile} className="admin-list-item">
                  <strong>{item.citizen_name}</strong>
                  <span className="badge">{item.mobile}</span>
                  <span className="badge secondary">{item.complaints} complaints</span>
                </li>
              ))
            )}
          </ul>
        </section>
      )}

      <AdminManagerModal
        type={activeManager}
        isOpen={!!activeManager}
        onClose={() => setActiveManager(null)}
        authToken={authToken}
        onRefresh={() => {
          // Trigger dashboard refresh by calling the parent's refresh mechanism
        }}
      />
    </>
  );
}

function Kpi({ label, value }) {
  return (
    <article className="kpi-card">
      <p>{label}</p>
      <h4>{value}</h4>
    </article>
  );
}

Kpi.propTypes = {
  label: PropTypes.string.isRequired,
  value: PropTypes.number.isRequired
};

RoleDashboard.propTypes = {
  role: PropTypes.oneOf(["citizen", "officer", "admin"]).isRequired,
  data: PropTypes.shape({
    summary: PropTypes.object,
    recent: PropTypes.array,
    ward: PropTypes.string,
    queue: PropTypes.array,
    officer_manager: PropTypes.array,
    department_manager: PropTypes.array,
    citizen_manager: PropTypes.array
  }),
  onStatusUpdate: PropTypes.func.isRequired,
  authToken: PropTypes.string.isRequired
};

RoleDashboard.defaultProps = {
  data: null
};

export default RoleDashboard;
