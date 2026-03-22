import { useMemo, useState } from "react";
import PropTypes from "prop-types";
import AdminManagerModal from "./AdminManagerModal";

function RoleDashboard({
  role,
  data,
  onStatusUpdate,
  authToken,
  user,
  isDark,
  onToggleTheme,
  onLogout
}) {
  if (!data) {
    return (
      <section className="card">
        <h3>Dashboard</h3>
        <p>Loading dashboard...</p>
      </section>
    );
  }

  if (role === "citizen") {
    return <CitizenDashboard data={data} />;
  }

  if (role === "officer") {
    return <OfficerDashboard data={data} onStatusUpdate={onStatusUpdate} />;
  }

  return (
    <AdminWorkspace
      data={data}
      authToken={authToken}
      user={user}
      isDark={isDark}
      onToggleTheme={onToggleTheme}
      onLogout={onLogout}
    />
  );
}

function CitizenDashboard({ data }) {
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

function OfficerDashboard({ data, onStatusUpdate }) {
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
                <button type="button" className="secondary" onClick={() => onStatusUpdate(item.ticket_id, "In Progress")}>
                  In Progress
                </button>
                <button type="button" onClick={() => onStatusUpdate(item.ticket_id, "Resolved")}>
                  Resolve
                </button>
              </div>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

function AdminWorkspace({ data, authToken, user, isDark, onToggleTheme, onLogout }) {
  const [activeManager, setActiveManager] = useState(null);
  const [activeSection, setActiveSection] = useState("dashboard");
  const adminSections = useMemo(
    () => [
      { id: "dashboard", label: "Dashboard" },
      { id: "complaints", label: "Complaints" },
      { id: "departments", label: "Departments" },
      { id: "officers", label: "Officers" },
      { id: "citizens", label: "Citizens" }
    ],
    []
  );

  const topOfficer = data.officer_manager?.[0] || null;
  const topDepartment = data.department_manager?.[0] || null;
  const topCitizen = data.citizen_manager?.[0] || null;
  const userName = user?.display_name || "Admin";
  const userHandle = user?.username || "admin";
  const initials = userName
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("") || "AD";

  return (
    <section className="admin-shell">
      <aside className="admin-sidebar">
        <div className="admin-brand">
          <h3>Public Service CRM</h3>
          <p>Admin Panel</p>
        </div>

        <nav className="admin-nav" aria-label="Admin navigation">
          {adminSections.map((section) => (
            <button
              key={section.id}
              type="button"
              className={`admin-nav-item ${activeSection === section.id ? "active" : ""}`}
              onClick={() => setActiveSection(section.id)}
            >
              {section.label}
            </button>
          ))}
        </nav>

        <div className="admin-sidebar-footer">
          <div className="admin-user-row">
            <span className="admin-avatar">{initials}</span>
            <div>
              <strong>{userName}</strong>
              <p>@{userHandle}</p>
            </div>
          </div>

          <div className="admin-footer-actions">
            <button type="button" className="theme-toggle" onClick={onToggleTheme}>
              <span className="toggle-dot" />
              <span>{isDark ? "Dark" : "Light"} Theme</span>
            </button>
            <button type="button" className="secondary" onClick={onLogout}>
              Logout
            </button>
          </div>
        </div>
      </aside>

      <section className="admin-content">{renderAdminContent({
        activeSection,
        data,
        topOfficer,
        topDepartment,
        topCitizen,
        setActiveManager
      })}</section>

      <AdminManagerModal
        type={activeManager}
        isOpen={!!activeManager}
        onClose={() => setActiveManager(null)}
        authToken={authToken}
        onRefresh={() => {
          // Trigger dashboard refresh by calling the parent's refresh mechanism
        }}
      />
    </section>
  );
}

function renderAdminContent({
  activeSection,
  data,
  topOfficer,
  topDepartment,
  topCitizen,
  setActiveManager
}) {
  if (activeSection === "dashboard") {
    return (
      <div className="admin-panel-stack">
        <header className="admin-panel-header">
          <h3>Dashboard</h3>
          <p>City-wide operational view across complaints, departments, officers, and citizens.</p>
        </header>

        <div className="kpi-grid admin-kpi-grid">
          <Kpi label="Total Complaints" value={data.summary.total_complaints} />
          <Kpi label="Open" value={data.summary.total_open} />
          <Kpi label="Resolved" value={data.summary.total_resolved} />
          <Kpi label="Active Officers" value={data.summary.active_officers} />
          <Kpi label="Departments" value={data.summary.total_departments} />
          <Kpi label="Citizens" value={data.summary.registered_citizens} />
        </div>

        <div className="admin-overview-grid">
          <article className="card">
            <h4>Highest Load</h4>
            <ul className="simple-list">
              <li>
                <strong>Department:</strong> {topDepartment?.name || "-"} ({topDepartment?.complaints || 0} complaints)
              </li>
              <li>
                <strong>Officer:</strong> {topOfficer?.display_name || "-"} ({topOfficer?.assigned_complaints || 0} complaints)
              </li>
              <li>
                <strong>Citizen Activity:</strong> {topCitizen?.citizen_name || "-"} ({topCitizen?.complaints || 0} complaints)
              </li>
            </ul>
          </article>

          <article className="card">
            <h4>Quick Governance Metrics</h4>
            <ul className="simple-list">
              <li>
                <strong>Resolution Rate:</strong>{" "}
                {data.summary.total_complaints > 0
                  ? `${Math.round((data.summary.total_resolved / data.summary.total_complaints) * 100)}%`
                  : "0%"}
              </li>
              <li>
                <strong>Open Workload:</strong> {data.summary.total_open} active cases
              </li>
              <li>
                <strong>Citizen Coverage:</strong> {data.summary.registered_citizens} registered citizens
              </li>
            </ul>
          </article>
        </div>
      </div>
    );
  }

  if (activeSection === "complaints") {
    return (
      <div className="admin-panel-stack">
        <header className="admin-panel-header">
          <h3>Complaints</h3>
          <p>Monitor live complaint pressure and routing concentration.</p>
        </header>

        <div className="kpi-grid">
          <Kpi label="Total Complaints" value={data.summary.total_complaints} />
          <Kpi label="Open Complaints" value={data.summary.total_open} />
          <Kpi label="Resolved Complaints" value={data.summary.total_resolved} />
        </div>

        <section className="card">
          <h4>Routing Pressure</h4>
          <ul className="simple-list">
            {data.department_manager?.slice(0, 5).map((item) => (
              <li key={item.id || item.name}>
                <strong>{item.name}</strong>: {item.complaints} complaints
              </li>
            ))}
          </ul>
        </section>
      </div>
    );
  }

  if (activeSection === "officers") {
    return (
      <ManagerPanel
        title="Officer Manager"
        emptyMessage="No officers. Click Manage to add."
        onManage={() => setActiveManager("officers")}
        items={data.officer_manager}
        renderItem={(item) => (
          <li key={item.username} className="admin-list-item">
            <strong>{item.display_name}</strong>
            <span className="badge">{item.ward || "No ward assigned"}</span>
            <span className="badge secondary">{item.assigned_complaints} complaints</span>
          </li>
        )}
      />
    );
  }

  if (activeSection === "departments") {
    return (
      <ManagerPanel
        title="Department Manager"
        emptyMessage="No departments. Click Manage to add."
        onManage={() => setActiveManager("departments")}
        items={data.department_manager}
        renderItem={(item) => (
          <li key={item.id || item.name} className="admin-list-item">
            <strong>{item.name}</strong>
            <span className="badge secondary">{item.complaints} complaints</span>
          </li>
        )}
      />
    );
  }

  if (activeSection === "citizens") {
    return (
      <ManagerPanel
        title="Citizen Manager"
        emptyMessage="No citizens. Click Manage to view."
        onManage={() => setActiveManager("citizens")}
        items={data.citizen_manager}
        renderItem={(item) => (
          <li key={item.mobile} className="admin-list-item">
            <strong>{item.citizen_name}</strong>
            <span className="badge">{item.mobile}</span>
            <span className="badge secondary">{item.complaints} complaints</span>
          </li>
        )}
      />
    );
  }

  return (
    <section className="card">
      <h4>Settings</h4>
      <p>Theme and session actions are available from the sidebar footer.</p>
    </section>
  );
}

function ManagerPanel({ title, emptyMessage, onManage, items, renderItem }) {
  return (
    <section className="card admin-manager-section">
      <div className="admin-manager-header">
        <h4>{title}</h4>
        <button type="button" className="secondary" onClick={onManage}>
          Manage
        </button>
      </div>
      <ul className="admin-list">
        {items?.length ? items.map((item) => renderItem(item)) : <li className="empty-state">{emptyMessage}</li>}
      </ul>
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

CitizenDashboard.propTypes = {
  data: PropTypes.shape({
    summary: PropTypes.object,
    recent: PropTypes.array
  }).isRequired
};

OfficerDashboard.propTypes = {
  data: PropTypes.shape({
    ward: PropTypes.string,
    summary: PropTypes.object,
    queue: PropTypes.array
  }).isRequired,
  onStatusUpdate: PropTypes.func.isRequired
};

AdminWorkspace.propTypes = {
  data: PropTypes.shape({
    summary: PropTypes.object,
    officer_manager: PropTypes.array,
    department_manager: PropTypes.array,
    citizen_manager: PropTypes.array
  }).isRequired,
  authToken: PropTypes.string.isRequired,
  user: PropTypes.shape({
    display_name: PropTypes.string,
    username: PropTypes.string
  }),
  isDark: PropTypes.bool,
  onToggleTheme: PropTypes.func,
  onLogout: PropTypes.func
};

AdminWorkspace.defaultProps = {
  user: null,
  isDark: false,
  onToggleTheme: () => {},
  onLogout: () => {}
};

ManagerPanel.propTypes = {
  title: PropTypes.string.isRequired,
  emptyMessage: PropTypes.string.isRequired,
  onManage: PropTypes.func.isRequired,
  items: PropTypes.array,
  renderItem: PropTypes.func.isRequired
};

ManagerPanel.defaultProps = {
  items: []
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
  authToken: PropTypes.string.isRequired,
  user: PropTypes.shape({
    display_name: PropTypes.string,
    username: PropTypes.string
  }),
  isDark: PropTypes.bool,
  onToggleTheme: PropTypes.func,
  onLogout: PropTypes.func
};

RoleDashboard.defaultProps = {
  data: null,
  user: null,
  isDark: false,
  onToggleTheme: () => {},
  onLogout: () => {}
};

export default RoleDashboard;
