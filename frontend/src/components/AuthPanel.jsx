import { useState } from "react";
import PropTypes from "prop-types";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:5000";

function AuthPanel({ onAuthenticated }) {
  const [mode, setMode] = useState("login");
  const [status, setStatus] = useState("");
  const [form, setForm] = useState({
    username: "",
    password: "",
    display_name: "",
    mobile: ""
  });

  const update = (event) => {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const submit = async (event) => {
    event.preventDefault();
    setStatus("Authenticating...");

    try {
      const endpoint = mode === "login" ? "/api/auth/login" : "/api/auth/register";
      const payload =
        mode === "login"
          ? { username: form.username, password: form.password }
          : {
              username: form.username,
              password: form.password,
              display_name: form.display_name,
              mobile: form.mobile
            };

      const response = await fetch(`${API_BASE}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      const result = await response.json();
      if (!response.ok) {
        throw new Error(result.error || "Authentication failed");
      }

      onAuthenticated(result);
      setStatus("Authenticated successfully.");
    } catch (error) {
      setStatus(error.message);
    }
  };

  return (
    <section className="card auth-card">
      <div className="auth-tabs" role="tablist" aria-label="Authentication mode">
        <button type="button" className={mode === "login" ? "active" : ""} onClick={() => setMode("login")}>
          Login
        </button>
        <button type="button" className={mode === "register" ? "active" : ""} onClick={() => setMode("register")}>
          Citizen Sign-up
        </button>
      </div>

      <form className="form-grid" onSubmit={submit}>
        <input
          name="username"
          value={form.username}
          onChange={update}
          placeholder="Username (email or id)"
          required
        />
        <input
          name="password"
          type="password"
          value={form.password}
          onChange={update}
          placeholder="Password"
          required
        />

        {mode === "register" && (
          <>
            <input
              name="display_name"
              value={form.display_name}
              onChange={update}
              placeholder="Full Name"
              required
            />
            <input name="mobile" value={form.mobile} onChange={update} placeholder="Mobile Number" required />
          </>
        )}

        <button type="submit">{mode === "login" ? "Login" : "Create Citizen Account"}</button>
      </form>

      <p className="status-text">{status}</p>
      <p className="helper-text">
        Officer/Admin credentials are controlled by backend environment variables.
      </p>
    </section>
  );
}

AuthPanel.propTypes = {
  onAuthenticated: PropTypes.func.isRequired
};

export default AuthPanel;
