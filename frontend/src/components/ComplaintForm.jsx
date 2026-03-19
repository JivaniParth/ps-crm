import { useState } from "react";
import PropTypes from "prop-types";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:5000";

function ComplaintForm({ predictedDepartment, authToken, onSubmitted }) {
  const [form, setForm] = useState({
    citizenName: "",
    mobile: "",
    description: "",
    latitude: "",
    longitude: ""
  });
  const [status, setStatus] = useState("");

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
          latitude: position.coords.latitude.toFixed(6),
          longitude: position.coords.longitude.toFixed(6)
        }));
      },
      () => {
        setStatus("Unable to fetch location. You can enter coordinates manually.");
      }
    );
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setStatus("Submitting grievance...");

    try {
      const payload = {
        citizen_name: form.citizenName,
        mobile: form.mobile,
        description: form.description,
        department: predictedDepartment,
        location: {
          latitude: Number(form.latitude),
          longitude: Number(form.longitude)
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
        latitude: "",
        longitude: ""
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
          placeholder="Describe the issue in detail"
          required
        />
        <div className="gps-row">
          <input name="latitude" value={form.latitude} onChange={updateField} placeholder="Latitude" required />
          <input name="longitude" value={form.longitude} onChange={updateField} placeholder="Longitude" required />
          <button type="button" className="secondary" onClick={attachGPS}>
            Attach GPS
          </button>
        </div>
        <button type="submit">Submit Complaint</button>
      </form>
      {status && <p className="status-text">{status}</p>}
    </section>
  );
}

ComplaintForm.propTypes = {
  predictedDepartment: PropTypes.string.isRequired,
  authToken: PropTypes.string.isRequired,
  onSubmitted: PropTypes.func.isRequired
};

export default ComplaintForm;
