import { useState } from "react";
import PropTypes from "prop-types";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:5000";

function AdminManagerModal({ type, isOpen, onClose, authToken, onRefresh }) {
  const [items, setItems] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState("");
  const [editingId, setEditingId] = useState(null);
  const [formData, setFormData] = useState({});
  const [showForm, setShowForm] = useState(false);

  // Fetch items when modal opens
  const fetchItems = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/admin/${type}`, {
        headers: { Authorization: `Bearer ${authToken}` }
      });
      if (response.ok) {
        const payload = await response.json();
        setItems(payload[type] || []);
      }
    } catch (error) {
      setStatus(`Error loading ${type}: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Fetch departments for officer assignment
  const fetchDepartmentsForForm = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/admin/departments`, {
        headers: { Authorization: `Bearer ${authToken}` }
      });
      if (response.ok) {
        const payload = await response.json();
        setDepartments(payload.departments || []);
      }
    } catch {
      // Silently fail if departments can't be fetched
    }
  };

  const handleFormChange = (e) => {
    const { name, value, type: inputType, checked } = e.target;
    if (inputType === "checkbox") {
      setFormData((prev) => ({
        ...prev,
        [name]: checked
          ? [...(prev[name] || []), value]
          : (prev[name] || []).filter((d) => d !== value)
      }));
    } else {
      setFormData((prev) => ({ ...prev, [name]: value }));
    }
  };

  const handleAdd = async (e) => {
    e.preventDefault();
    setStatus("Saving...");
    try {
      const response = await fetch(`${API_BASE}/api/admin/${type}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${authToken}`
        },
        body: JSON.stringify(formData)
      });
      if (response.ok) {
        setStatus(`${type} added successfully`);
        setFormData({});
        setShowForm(false);
        fetchItems();
        onRefresh?.();
      } else {
        const error = await response.json();
        setStatus(`Error: ${error.error || "Failed to add"}`);
      }
    } catch (error) {
      setStatus(`Error: ${error.message}`);
    }
  };

  const handleUpdate = async (e) => {
    e.preventDefault();
    setStatus("Updating...");
    try {
      const response = await fetch(`${API_BASE}/api/admin/${type}/${editingId}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${authToken}`
        },
        body: JSON.stringify(formData)
      });
      if (response.ok) {
        setStatus(`${type} updated successfully`);
        setFormData({});
        setEditingId(null);
        setShowForm(false);
        fetchItems();
        onRefresh?.();
      } else {
        const error = await response.json();
        setStatus(`Error: ${error.error || "Failed to update"}`);
      }
    } catch (error) {
      setStatus(`Error: ${error.message}`);
    }
  };

  const handleDelete = async (id) => {
    if (!globalThis.confirm(`Are you sure you want to delete this ${type.slice(0, -1)}?`)) {
      return;
    }
    setStatus("Deleting...");
    try {
      const response = await fetch(`${API_BASE}/api/admin/${type}/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${authToken}` }
      });
      if (response.ok) {
        setStatus(`${type} deleted successfully`);
        fetchItems();
        onRefresh?.();
      } else {
        const error = await response.json();
        setStatus(`Error: ${error.error || "Failed to delete"}`);
      }
    } catch (error) {
      setStatus(`Error: ${error.message}`);
    }
  };

  const handleEdit = (item) => {
    setEditingId(item.id || item.username || item.name);
    setFormData(item);
    if (type === "officers") {
      fetchDepartmentsForForm();
    }
    setShowForm(true);
  };

  const handleCloseModal = () => {
    setFormData({});
    setEditingId(null);
    setShowForm(false);
    setStatus("");
    onClose();
  };

  if (!isOpen) return null;

  const handleOverlayClick = (e) => {
    if (e.target === e.currentTarget) {
      handleCloseModal();
    }
  };

  const handleOverlayKeyDown = (e) => {
    if (e.key === "Escape") {
      handleCloseModal();
    }
  };

  return (
    <div
      className="modal-overlay"
      onClick={handleOverlayClick}
      onKeyDown={handleOverlayKeyDown}
      role="presentation"
    >
      <div className="modal-content" role="dialog" aria-labelledby="modal-title">
        <div className="modal-header">
          <h3 id="modal-title">{type.charAt(0).toUpperCase() + type.slice(1)}</h3>
          <button type="button" className="modal-close" onClick={handleCloseModal}>
            ✕
          </button>
        </div>

        <div className="modal-body">
          {showForm ? (
            <form onSubmit={editingId ? handleUpdate : handleAdd} className="form-grid">
              {type === "officers" && (
                <>
                  <input
                    type="email"
                    name="username"
                    placeholder="Email (e.g., officer@pscrm.gov)"
                    value={formData.username || ""}
                    onChange={handleFormChange}
                    disabled={!!editingId}
                    required
                  />
                  <input
                    type="text"
                    name="display_name"
                    placeholder="Display Name"
                    value={formData.display_name || ""}
                    onChange={handleFormChange}
                    required
                  />
                  <input
                    type="text"
                    name="ward"
                    placeholder="Ward (e.g., Ward-12)"
                    value={formData.ward || ""}
                    onChange={handleFormChange}
                    required
                  />
                  {!editingId && (
                    <input
                      type="password"
                      name="password"
                      placeholder="Password"
                      value={formData.password || ""}
                      onChange={handleFormChange}
                      required
                    />
                  )}
                  <fieldset className="checkbox-group">
                    <legend>Assign Departments</legend>
                    {departments.map((dept) => (
                      <label key={dept.id || dept.name}>
                        <input
                          type="checkbox"
                          name="departments"
                          value={dept.name}
                          checked={(formData.departments || []).includes(dept.name)}
                          onChange={handleFormChange}
                        />
                        {dept.name}
                      </label>
                    ))}
                  </fieldset>
                </>
              )}
              {type === "departments" && (
                <>
                  <input
                    type="text"
                    name="name"
                    placeholder="Department Name (e.g., Roads, Water)"
                    value={formData.name || ""}
                    onChange={handleFormChange}
                    disabled={!!editingId}
                    required
                  />
                  <textarea
                    name="description"
                    placeholder="Description"
                    value={formData.description || ""}
                    onChange={handleFormChange}
                    rows="3"
                  />
                </>
              )}
              {type === "citizens" && (
                <>
                  <input
                    type="text"
                    name="citizen_name"
                    placeholder="Citizen Name"
                    value={formData.citizen_name || ""}
                    onChange={handleFormChange}
                    disabled
                  />
                  <input
                    type="tel"
                    name="mobile"
                    placeholder="Mobile"
                    value={formData.mobile || ""}
                    onChange={handleFormChange}
                    disabled
                  />
                  <p className="helper-text">Citizen information is read-only. View submitted complaints above.</p>
                </>
              )}
              <div className="button-row">
                <button type="button" className="secondary" onClick={() => setShowForm(false)}>
                  Cancel
                </button>
                <button type="submit">{editingId ? "Update" : "Add"}</button>
              </div>
            </form>
          ) : (
            <>
              {loading && <p>Loading {type}...</p>}
              {!loading && (
                <>
                  <button
                    type="button"
                    className="secondary"
                    onClick={() => {
                      setShowForm(true);
                      if (type === "officers") {
                        fetchDepartmentsForForm();
                      }
                    }}
                  >
                    + Add New {type.slice(0, -1).charAt(0).toUpperCase() + type.slice(1, -1)}
                  </button>
                  <div className="manager-list">
                    {items.length === 0 && <p>No {type} yet.</p>}
                    {items.map((item) => (
                      <div key={item.id || item.username || item.name} className="manager-item">
                        <div className="item-info">
                          {type === "officers" && (
                            <>
                              <strong>{item.display_name}</strong>
                              <p>{item.username}</p>
                              <p className="helper-text">{item.ward}</p>
                              {item.departments && item.departments.length > 0 && (
                                <p className="helper-text">Departments: {item.departments.join(", ")}</p>
                              )}
                            </>
                          )}
                          {type === "departments" && (
                            <>
                              <strong>{item.name}</strong>
                              {item.description && <p>{item.description}</p>}
                            </>
                          )}
                          {type === "citizens" && (
                            <>
                              <strong>{item.citizen_name}</strong>
                              <p>{item.mobile}</p>
                              <p className="helper-text">{item.complaints} complaints</p>
                            </>
                          )}
                        </div>
                        <div className="item-actions">
                          {type !== "citizens" && (
                            <button
                              type="button"
                              className="secondary"
                              onClick={() => handleEdit(item)}
                            >
                              Edit
                            </button>
                          )}
                          <button
                            type="button"
                            className="danger"
                            onClick={() => handleDelete(item.id || item.username || item.name)}
                          >
                            Delete
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </>
          )}
        </div>

        {status && <p className="status-text" style={{ padding: "0.5rem 1rem" }}>{status}</p>}
      </div>
    </div>
  );
}

AdminManagerModal.propTypes = {
  type: PropTypes.oneOf(["officers", "departments", "citizens"]).isRequired,
  isOpen: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  authToken: PropTypes.string.isRequired,
  onRefresh: PropTypes.func
};

export default AdminManagerModal;
