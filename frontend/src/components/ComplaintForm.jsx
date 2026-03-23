import { useState } from "react";
import PropTypes from "prop-types";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:5000";

function ComplaintForm({ authToken, onSubmitted }) {
  const [form, setForm] = useState({
    citizenName: "",
    mobile: "",
    description: "",
    department: "",
    incident_latitude: "",
    incident_longitude: "",
    reporting_latitude: "",
    reporting_longitude: ""
  });
  const [status, setStatus] = useState("");
  const [duplicates, setDuplicates] = useState([]);

  useEffect(() => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          setForm((prev) => ({
            ...prev,
            reporting_latitude: pos.coords.latitude.toFixed(6),
            reporting_longitude: pos.coords.longitude.toFixed(6)
          }));
        },
        () => console.warn("Failed to get reporting location.")
      );
    }
  }, []);

  useEffect(() => {
    const checkDuplicates = async () => {
      if (form.incident_latitude && form.incident_longitude && form.department) {
        try {
          const res = await fetch(`${API_BASE}/api/complaints/duplicates?lat=${form.incident_latitude}&lng=${form.incident_longitude}&category=${encodeURIComponent(form.department)}`);
          if (res.ok) {
            const data = await res.json();
            setDuplicates(data.duplicates || []);
          }
        } catch (err) {
          console.error("Duplicate check failed:", err);
        }
      } else {
        setDuplicates([]);
      }
    };
    checkDuplicates();
  }, [form.incident_latitude, form.incident_longitude, form.department]);

  const updateField = (event) => {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const attachGPS = () => {
    if (!navigator.geolocation) {
      setStatus("Geolocation is not supported by this browser.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setForm((prev) => ({
          ...prev,
          incident_latitude: position.coords.latitude.toFixed(6),
          incident_longitude: position.coords.longitude.toFixed(6)
        }));
      },
      () => {
        setStatus("Unable to fetch location. You can enter coordinates manually.");
      }
    );
  };

  const handleBlur = async () => {
    if (!form.description) return;
    try {
      const res = await fetch(`${API_BASE}/api/classify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: form.description })
      });
      if (res.ok) {
        const data = await res.json();
        if (data.department) {
          setForm(prev => ({ ...prev, department: data.department }));
        }
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setStatus("Submitting grievance...");

    try {
      const payload = {
        citizen_name: form.citizenName,
        mobile: form.mobile,
        description: form.description,
        department: form.department,
        location: {
          incident_latitude: Number(form.incident_latitude),
          incident_longitude: Number(form.incident_longitude),
          reporting_latitude: Number(form.reporting_latitude),
          reporting_longitude: Number(form.reporting_longitude)
        },
        channel: "web"
      };

      const response = await fetch(`${API_BASE}/api/complaints`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${authToken}`
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        throw new Error("Unable to submit complaint");
      }

      const result = await response.json();
      setStatus(`Submitted successfully. Ticket: ${result.ticket_id}`);
      onSubmitted(result);
      setForm({
        citizenName: "",
        mobile: "",
        description: "",
        department: "",
        incident_latitude: "",
        incident_longitude: "",
        reporting_latitude: "",
        reporting_longitude: ""
      });
    } catch (error) {
      setStatus(error.message);
    }
  };

  return (
    <section className="card">
      <h3>Register Grievance</h3>
      <form className="form-grid" onSubmit={handleSubmit}>
        <input name="citizenName" value={form.citizenName} onChange={updateField} placeholder="Citizen Name" required />
        <input name="mobile" value={form.mobile} onChange={updateField} placeholder="Mobile Number" required />
        <textarea
          name="description"
          rows={4}
          value={form.description}
          onChange={updateField}
          onBlur={handleBlur}
          placeholder="Describe the issue in detail"
          required
        />
        <select name="department" value={form.department} onChange={updateField} required>
          <option value="" disabled>Select Department</option>
          <option value="Roads & Highways">Roads & Highways</option>
          <option value="Water Supply & Sanitation">Water Supply & Sanitation</option>
          <option value="Public Health Department">Public Health Department</option>
          <option value="General Grievance">General Grievance</option>
        </select>
        <div className="gps-row">
          <input name="incident_latitude" value={form.incident_latitude} onChange={updateField} placeholder="Latitude" required />
          <input name="incident_longitude" value={form.incident_longitude} onChange={updateField} placeholder="Longitude" required />
          <button type="button" className="secondary" onClick={attachGPS}>
            Attach GPS
          </button>
        </div>

        {duplicates.length > 0 && (
          <div className="card duplicates-warning" style={{ background: "var(--bg-warning, #fff3cd)", borderColor: "var(--border-warning, #ffeeba)" }}>
            <h4>Similar reports nearby</h4>
            <ul className="simple-list" style={{ marginTop: '0.5rem' }}>
              {duplicates.map((dup) => (
                <li key={dup.ticket_id}>
                  <strong>{dup.ticket_id}</strong> - {dup.status}
                </li>
              ))}
            </ul>
            <p style={{ marginTop: '0.5rem', fontSize: '0.85rem' }}>Consider tracking an existing report rather than submitting a duplicate.</p>
          </div>
        )}

        <button type="submit">Submit Complaint</button>
      </form>
      {status && <p className="status-text">{status}</p>}
    </section>
  );
}

ComplaintForm.propTypes = {
  authToken: PropTypes.string.isRequired,
  onSubmitted: PropTypes.func.isRequired
};

export default ComplaintForm;
