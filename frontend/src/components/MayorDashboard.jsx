import PropTypes from "prop-types";
import AnalyticsDashboard from "./AnalyticsDashboard";

function MayorDashboard({ data, statusData, departmentData }) {
  if (!data) {
    return (
      <section className="card">
        <h3>Mayor Dashboard</h3>
        <p>Loading city-wide analytics...</p>
      </section>
    );
  }

  return (
    <section className="stack mayor-stack">
      <section className="card">
        <h3>Mayor Dashboard</h3>
        <p>City-wide analytics across all complaint types and service categories.</p>
        <div className="kpi-grid">
          <Kpi label="Total Complaints" value={data.summary.total_complaints} />
          <Kpi label="Open" value={data.summary.open_complaints} />
          <Kpi label="Resolved" value={data.summary.resolved_complaints} />
          <Kpi label="Escalated" value={data.summary.escalated_complaints} />
        </div>
      </section>

      <AnalyticsDashboard statusData={statusData} departmentData={departmentData} title="Mayor Analytics" />

      <section className="card">
        <h4>Complaint Types by Volume</h4>
        <ul className="simple-list">
          {departmentData.length === 0 && <li>No complaints registered yet.</li>}
          {departmentData.map((item) => (
            <li key={item.name}>
              {item.name} - {item.complaints}
            </li>
          ))}
        </ul>
      </section>
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

MayorDashboard.propTypes = {
  data: PropTypes.shape({
    summary: PropTypes.shape({
      total_complaints: PropTypes.number.isRequired,
      open_complaints: PropTypes.number.isRequired,
      resolved_complaints: PropTypes.number.isRequired,
      escalated_complaints: PropTypes.number.isRequired
    }).isRequired
  }),
  statusData: PropTypes.arrayOf(
    PropTypes.shape({
      name: PropTypes.string.isRequired,
      value: PropTypes.number.isRequired
    })
  ).isRequired,
  departmentData: PropTypes.arrayOf(
    PropTypes.shape({
      name: PropTypes.string.isRequired,
      complaints: PropTypes.number.isRequired
    })
  ).isRequired
};

MayorDashboard.defaultProps = {
  data: null
};

export default MayorDashboard;