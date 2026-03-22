import { useEffect, useMemo, useState } from "react";
import AnalyticsDashboard from "./components/AnalyticsDashboard";
import AuthPanel from "./components/AuthPanel";
import ComplaintForm from "./components/ComplaintForm";
import MayorDashboard from "./components/MayorDashboard";
import NLPDemo from "./components/NLPDemo";
import RoleDashboard from "./components/RoleDashboard";
import ResolutionTimeline from "./components/ResolutionTimeline";
import ThemeToggle from "./components/ThemeToggle";
import { useTheme } from "./hooks/useTheme";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:5000";
const AUTH_KEY = "pscrm-auth";

function App() {
  const { isDark, toggleTheme } = useTheme();
  const [prediction, setPrediction] = useState({ department: "General Grievance", confidence: 0.4 });
  const [auth, setAuth] = useState({ token: "", user: null });
  const [authReady, setAuthReady] = useState(false);
  const [ticket, setTicket] = useState(null);
  const [dashboardData, setDashboardData] = useState(null);
  const [globalStatus, setGlobalStatus] = useState("");
  const [timelineIndex, setTimelineIndex] = useState(1);
  const [statusData, setStatusData] = useState([
    { name: "Open", value: 7 },
    { name: "In Progress", value: 5 },
    { name: "Escalated", value: 2 },
    { name: "Resolved", value: 11 }
  ]);
  const [departmentData, setDepartmentData] = useState([
    { name: "Roads", complaints: 12 },
    { name: "Water", complaints: 8 },
    { name: "Electricity", complaints: 6 }
  ]);
  const isAuthenticated = Boolean(auth.user);

  useEffect(() => {
    const raw = localStorage.getItem(AUTH_KEY);
    if (!raw) {
      setAuthReady(true);
      return;
    }

    try {
      const parsed = JSON.parse(raw);
      if (!parsed?.token) {
        setAuthReady(true);
        return;
      }

      fetch(`${API_BASE}/api/auth/me`, {
        headers: { Authorization: `Bearer ${parsed.token}` }
      })
        .then((response) => {
          if (!response.ok) {
            throw new Error("session expired");
          }
          return response.json();
        })
        .then((payload) => {
          setAuth({ token: parsed.token, user: payload.user });
        })
        .catch(() => {
          localStorage.removeItem(AUTH_KEY);
        })
        .finally(() => setAuthReady(true));
    } catch {
      localStorage.removeItem(AUTH_KEY);
      setAuthReady(true);
    }
  }, []);

  useEffect(() => {
    if (!auth.user || !auth.token) {
      setDashboardData(null);
      return;
    }

    const roleEndpoint = {
      citizen: "citizen",
      officer: "officer",
      admin: "admin",
      mayor: "mayor"
    }[auth.user.role];

    if (!roleEndpoint) {
      return;
    }

    const fetchDashboard = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/dashboard/${roleEndpoint}`, {
          headers: { Authorization: `Bearer ${auth.token}` }
        });
        if (!response.ok) return;
        const payload = await response.json();
        setDashboardData(payload);

        if (auth.user.role === "mayor" && payload.analytics) {
          setStatusData(payload.analytics.status_breakdown);
          setDepartmentData(payload.analytics.department_volume);
        }
      } catch {
        // Keep local fallback values when API is not yet available.
      }
    };

    fetchDashboard();
  }, [auth]);

  useEffect(() => {
    if (!["officer"].includes(auth.user?.role || "") || !auth.token) {
      return;
    }

    const fetchAnalytics = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/analytics`, {
          headers: { Authorization: `Bearer ${auth.token}` }
        });
        if (!response.ok) return;
        const payload = await response.json();
        setStatusData(payload.status_breakdown);
        setDepartmentData(payload.department_volume);
      } catch {
        // Keep local fallback values when API is not yet available.
      }
    };

    fetchAnalytics();
  }, [auth.token, auth.user]);

  useEffect(() => {
    if (!ticket?.ticket_id) {
      return;
    }

    const poll = setInterval(async () => {
      try {
        const response = await fetch(`${API_BASE}/api/complaints/${ticket.ticket_id}/timeline`);
        if (!response.ok) return;
        const payload = await response.json();
        const active = payload.steps.findIndex((item) => item.status !== "Completed");
        setTimelineIndex(active === -1 ? payload.steps.length - 1 : Math.max(0, active - 1));
      } catch {
        // Silent polling failure for local dev resilience.
      }
    }, 5000);

    return () => clearInterval(poll);
  }, [ticket]);

  const handleAuthenticated = ({ token, user }) => {
    const next = { token, user };
    localStorage.setItem(AUTH_KEY, JSON.stringify(next));
    setAuth(next);
    setGlobalStatus(`Welcome, ${user.display_name}`);
  };

  const handleLogout = async () => {
    if (auth.token) {
      try {
        await fetch(`${API_BASE}/api/auth/logout`, {
          method: "POST",
          headers: { Authorization: `Bearer ${auth.token}` }
        });
      } catch {
        // Ignore logout network errors and clear local session anyway.
      }
    }

    localStorage.removeItem(AUTH_KEY);
    setAuth({ token: "", user: null });
    setDashboardData(null);
    setGlobalStatus("Logged out.");
  };

  const updateTicketStatus = async (ticketId, status) => {
    try {
      const response = await fetch(`${API_BASE}/api/complaints/${ticketId}/status`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${auth.token}`
        },
        body: JSON.stringify({ status })
      });

      if (!response.ok) {
        throw new Error("Unable to update status");
      }

      setGlobalStatus(`Updated ${ticketId} to ${status}.`);

      const roleEndpoint = auth.user.role;
      const refreshed = await fetch(`${API_BASE}/api/dashboard/${roleEndpoint}`, {
        headers: { Authorization: `Bearer ${auth.token}` }
      });
      if (refreshed.ok) {
        setDashboardData(await refreshed.json());
      }
    } catch (error) {
      setGlobalStatus(error.message);
    }
  };

  const tagline = useMemo(
    () =>
      "Every Citizen's Voice, from submission to automated routing and transparent resolution.",
    []
  );
  const role = auth.user?.role || "";
  const isAdminView = isAuthenticated && role === "admin";
  let mainContent;

  if (isAuthenticated && role === "admin") {
    mainContent = (
      <main className="layout-grid layout-single admin-main-content">
        <RoleDashboard
          role={role}
          data={dashboardData}
          onStatusUpdate={updateTicketStatus}
          authToken={auth.token}
          user={auth.user}
          isDark={isDark}
          onToggleTheme={toggleTheme}
          onLogout={handleLogout}
        />
      </main>
    );
  } else if (isAuthenticated && role === "mayor") {
    mainContent = (
      <main className="layout-grid layout-single">
        <MayorDashboard data={dashboardData} authToken={auth.token} />
      </main>
    );
  } else if (isAuthenticated) {
    mainContent = (
      <main className="layout-grid">
        <div className="stack">
          {role === "citizen" && <NLPDemo onPrediction={setPrediction} />}
          {role === "citizen" && (
            <ComplaintForm
              predictedDepartment={prediction.department}
              authToken={auth.token}
              onSubmitted={(submission) => {
                setTicket(submission);
                setTimelineIndex(0);
              }}
            />
          )}
          {role === "officer" && (
            <section className="card">
              <h3>Officer Console</h3>
              <p>Use the queue controls to move complaints through their lifecycle.</p>
            </section>
          )}
        </div>

        <div className="stack">
          <ResolutionTimeline currentStep={timelineIndex} ticket={ticket} />
          {ticket && (
            <section className="card">
              <h3>Live Ticket Snapshot</h3>
              <p>
                <strong>Ticket ID:</strong> {ticket.ticket_id}
              </p>
              <p>
                <strong>Assigned To:</strong> {ticket.assigned_officer}
              </p>
              <p>
                <strong>Ward:</strong> {ticket.ward}
              </p>
              <p>
                <strong>Status:</strong> {ticket.status}
              </p>
            </section>
          )}
          <RoleDashboard
            role={role}
            data={dashboardData}
            onStatusUpdate={updateTicketStatus}
            authToken={auth.token}
          />
        </div>
      </main>
    );
  } else {
    mainContent = (
      <main className="layout-grid">
        <AuthPanel onAuthenticated={handleAuthenticated} />
        <section className="card">
          <h3>Access Roles</h3>
          <ul className="simple-list">
            <li>Citizen: Register and submit grievances, track your tickets.</li>
            <li>Officer: Review ward queue and update status.</li>
            <li>Admin: Manage officers, departments, and citizen grievance activity.</li>
            <li>Mayor: Monitor city-wide analytics for all complaint types.</li>
          </ul>
        </section>
      </main>
    );
  }

  if (!authReady) {
    return (
      <div className="app-shell">
        <section className="card">
          <h3>Preparing secure session...</h3>
        </section>
      </div>
    );
  }

  return (
    <div className={`app-shell ${isAdminView ? "admin-app-shell" : ""}`}>
      {!isAdminView && (
        <header className="hero">
          <div>
            <p className="kicker">National Public Grievance Grid</p>
            <h1>Public Service CRM</h1>
            <p>{tagline}</p>
            {auth.user && <p className="helper-text">Logged in as {auth.user.display_name} ({auth.user.role})</p>}
          </div>
          <div className="hero-actions">
            <ThemeToggle isDark={isDark} onToggle={toggleTheme} />
            {auth.user && (
              <button type="button" className="secondary" onClick={handleLogout}>
                Logout
              </button>
            )}
          </div>
        </header>
      )}

      {mainContent}

      {auth.user && ["officer"].includes(auth.user.role) && (
        <AnalyticsDashboard statusData={statusData} departmentData={departmentData} />
      )}

      {globalStatus && !isAdminView && <p className="status-text global-status">{globalStatus}</p>}
    </div>
  );
}

export default App;
