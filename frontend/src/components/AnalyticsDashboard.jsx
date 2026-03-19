import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import PropTypes from "prop-types";

const STATUS_COLORS = ["#00d4ff", "#0057ff", "#00ff99", "#14b8a6"];

function AnalyticsDashboard({ statusData, departmentData, title }) {
  return (
    <section className="card chart-card">
      <h3>{title}</h3>
      <div className="charts-grid">
        <div>
          <h4>Status Breakdown</h4>
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie data={statusData} dataKey="value" nameKey="name" outerRadius={90} fill="#00d4ff" label>
                {statusData.map((entry, index) => (
                  <Cell key={entry.name} fill={STATUS_COLORS[index % STATUS_COLORS.length]} />
                ))}
              </Pie>
              <Legend />
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div>
          <h4>Department Volume</h4>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={departmentData}>
              <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.25} />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="complaints" fill="#0057ff" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </section>
  );
}

AnalyticsDashboard.propTypes = {
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
  ).isRequired,
  title: PropTypes.string
};

AnalyticsDashboard.defaultProps = {
  title: "Analytics Dashboard"
};

export default AnalyticsDashboard;
