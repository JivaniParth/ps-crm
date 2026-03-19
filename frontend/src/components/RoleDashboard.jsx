import PropTypes from "prop-types";

function RoleDashboard({ role, data, onStatusUpdate }) {
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

      <div className="admin-manager-grid">
        <section className="manager-card">
          <h4>Officer Manager</h4>
          <ul className="simple-list">
            {data.officer_manager.length === 0 && <li>No active officer assignments yet.</li>}
            {data.officer_manager.map((item) => (
              <li key={item.officer}>
                {item.officer} - {item.assigned_complaints} assigned
              </li>
            ))}
          </ul>
        </section>

        <section className="manager-card">
          <h4>Department Manager</h4>
          <ul className="simple-list">
            {data.department_manager.length === 0 && <li>No department traffic yet.</li>}
            {data.department_manager.map((item) => (
              <li key={item.department}>
                {item.department} - {item.complaints} complaints
              </li>
            ))}
          </ul>
        </section>

        <section className="manager-card">
          <h4>Citizen Manager</h4>
          <ul className="simple-list">
            {data.citizen_manager.length === 0 && <li>No citizen submissions yet.</li>}
            {data.citizen_manager.map((item) => (
              <li key={item.mobile}>
                {item.citizen_name} ({item.mobile}) - {item.complaints} complaints
              </li>
            ))}
          </ul>
        </section>
      </div>
    </section>
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
  onStatusUpdate: PropTypes.func.isRequired
};

RoleDashboard.defaultProps = {
  data: null
};

export default RoleDashboard;
