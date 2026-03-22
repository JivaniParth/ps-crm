import { useState, useCallback } from "react";
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

  // Determine the key array from the payload based on type
  const payloadKeyMap = {
    registry: "regions"
  };

  const itemIdKey = (item) => item.region_key || item.layer_id || item.id || item.username || item.name;

  // Fetch items when modal opens
  const fetchItems = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/admin/${type}`, {
        headers: { Authorization: `Bearer ${authToken}` }
      });
      if (response.ok) {
        const payload = await response.json();
        const key = payloadKeyMap[type] || type;
        setItems(payload[key] || []);
      } else {
        setStatus(`Failed to load ${type}`);
      }
    } catch (error) {
      setStatus(`Error loading ${type}: ${error.message}`);
    } finally {
      setLoading(false);
    }
  }, [authToken, type, payloadKeyMap]);

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

  const handleJsonChange = (e) => {
    const { name, value } = e.target;
    try {
      const parsed = JSON.parse(value);
      setFormData((prev) => ({ ...prev, [name]: parsed, [`${name}_raw`]: value }));
    } catch {
      setFormData((prev) => ({ ...prev, [`${name}_raw`]: value }));
    }
  }

  const handleAdd = async (e) => {
    e.preventDefault();
    setStatus("Saving...");
    try {
      // Clean up raw json fields before sending
      const cleanData = { ...formData };
      Object.keys(cleanData).forEach(k => { if (k.endsWith('_raw')) delete cleanData[k]; });

      const response = await fetch(`${API_BASE}/api/admin/${type}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${authToken}`
        },
        body: JSON.stringify(cleanData)
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
      const cleanData = { ...formData };
      Object.keys(cleanData).forEach(k => { if (k.endsWith('_raw')) delete cleanData[k]; });

      const response = await fetch(`${API_BASE}/api/admin/${type}/${editingId}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${authToken}`
        },
        body: JSON.stringify(cleanData)
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
    let confirmMsg = `Are you sure you want to delete this ${type.slice(0, -1)}?`;
    if (type === "registry") confirmMsg = "Are you sure you want to deregister this regional database?";

    if (!globalThis.confirm(confirmMsg)) {
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
    setEditingId(itemIdKey(item));
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

  // React hook triggers
  if (isOpen && items.length === 0 && !loading && !status) {
    fetchItems();
  }

  const handleOverlayClick = (e) => {
    if (e.target === e.currentTarget) handleCloseModal();
  };

  const handleOverlayKeyDown = (e) => {
    if (e.key === "Escape") handleCloseModal();
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
          <button type="button" className="modal-close" onClick={handleCloseModal}>✕</button>
        </div>

        <div className="modal-body">
          {showForm ? (
            <form onSubmit={editingId ? handleUpdate : handleAdd} className="form-grid">

              {type === "officers" && (
                <>
                  <input type="email" name="username" placeholder="Email (e.g., officer@pscrm.gov)" value={formData.username || ""} onChange={handleFormChange} disabled={!!editingId} required />
                  <input type="text" name="display_name" placeholder="Display Name" value={formData.display_name || ""} onChange={handleFormChange} required />
                  <input type="text" name="ward" placeholder="Ward (e.g., Ward-12)" value={formData.ward || ""} onChange={handleFormChange} required />
                  {!editingId && <input type="password" name="password" placeholder="Password" value={formData.password || ""} onChange={handleFormChange} required />}
                  <fieldset className="checkbox-group">
                    <legend>Assign Departments</legend>
                    {departments.map((dept) => (
                      <label key={dept.id || dept.name}>
                        <input type="checkbox" name="departments" value={dept.name} checked={(formData.departments || []).includes(dept.name)} onChange={handleFormChange} />
                        {dept.name}
                      </label>
                    ))}
                  </fieldset>
                </>
              )}

              {type === "departments" && (
                <>
                  <input type="text" name="name" placeholder="Department Name (e.g., Roads, Water)" value={formData.name || ""} onChange={handleFormChange} disabled={!!editingId} required />
                  <textarea name="description" placeholder="Description" value={formData.description || ""} onChange={handleFormChange} rows="3" />
                </>
              )}

              {type === "registry" && (
                <>
                  <input type="text" name="region_key" placeholder="Region Key (e.g., MH-MUM)" value={formData.region_key || ""} onChange={handleFormChange} disabled={!!editingId} required />
                  <input type="text" name="db_url" placeholder="Database DSN URL (e.g., sqlite:///region.db)" value={formData.db_url || ""} onChange={handleFormChange} required />
                  <select name="tier" value={formData.tier || "Local"} onChange={handleFormChange} style={{ padding: '0.72rem', borderRadius: '12px', borderColor: 'color-mix(in srgb, var(--text) 15%, transparent)', background: 'var(--surface)', color: 'var(--text)' }} required>
                    <option value="Local">Local (ULB / City)</option>
                    <option value="State">State</option>
                    <option value="Central">Central</option>
                  </select>
                  <input type="text" name="display_name" placeholder="Display Name (e.g., Mumbai Municipal Corp)" value={formData.display_name || ""} onChange={handleFormChange} required />
                  <p className="helper-text">Registering a new DB endpoint dynamically enables API routing for the specified region.</p>
                </>
              )}

              {type === "jurisdictions" && (
                <>
                  <select name="tier" value={formData.tier || "Local"} onChange={handleFormChange} style={{ padding: '0.72rem', borderRadius: '12px', borderColor: 'color-mix(in srgb, var(--text) 15%, transparent)', background: 'var(--surface)', color: 'var(--text)' }} required>
                    <option value="Local">Local</option>
                    <option value="State">State</option>
                    <option value="Central">Central</option>
                  </select>
                  <input type="text" name="authority_name" placeholder="Authority Name (e.g., NHAI, PWD)" value={formData.authority_name || ""} onChange={handleFormChange} required />
                  <input type="text" name="department_id" placeholder="Department ID (slug)" value={formData.department_id || ""} onChange={handleFormChange} required />
                  <input type="text" name="asset_type" placeholder="Asset Type (e.g., road, drain)" value={formData.asset_type || ""} onChange={handleFormChange} required />
                  <input type="number" name="priority_weight" placeholder="Priority Weight (higher = stronger claim)" value={formData.priority_weight || ""} onChange={handleFormChange} required />
                  <textarea name="geojson" placeholder='GeoJSON Polygon (e.g. {"type": "Polygon", "coordinates": [...]})' value={formData.geojson_raw || JSON.stringify(formData.geojson) || ""} onChange={handleJsonChange} rows="5" required />
                  <p className="helper-text">Jurisdiction layers are used for spatial queries to calculate overlap priorities when citizen tickets are submitted.</p>
                </>
              )}

              {type === "citizens" && (
                <>
                  <input type="text" name="citizen_name" placeholder="Citizen Name" value={formData.citizen_name || ""} onChange={handleFormChange} disabled />
                  <input type="tel" name="mobile" placeholder="Mobile" value={formData.mobile || ""} onChange={handleFormChange} disabled />
                  <p className="helper-text">Citizen information is read-only.</p>
                </>
              )}

              <div className="button-row">
                <button type="button" className="secondary" onClick={() => setShowForm(false)}>Cancel</button>
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
                      setFormData(type === "registry" ? { tier: "Local" } : (type === "jurisdictions" ? { tier: "Local", priority_weight: 10 } : {}));
                      setShowForm(true);
                      if (type === "officers") fetchDepartmentsForForm();
                    }}
                  >
                    + Add New {type === "registry" ? "Regional DB" : type === "jurisdictions" ? "Jurisdiction Layer" : type.slice(0, -1).charAt(0).toUpperCase() + type.slice(1, -1)}
                  </button>
                  <div className="manager-list">
                    {items.length === 0 && <p>No {type} found.</p>}
                    {items.map((item) => (
                      <div key={itemIdKey(item)} className="manager-item">
                        <div className="item-info">
                          {type === "registry" && (
                            <>
                              <strong>{item.display_name}</strong>
                              <p className="helper-text"><span className={`badge tier-${item.tier.toLowerCase()}`}>{item.tier}</span> {item.region_key}</p>
                              <p className="helper-text" style={{ wordBreak: 'break-all', fontSize: '0.8rem' }}>{item.db_url}</p>
                            </>
                          )}
                          {type === "jurisdictions" && (
                            <>
                              <strong>{item.authority_name}</strong>
                              <p className="helper-text"><span className={`badge tier-${item.tier?.toLowerCase()}`}>{item.tier}</span> Asset: {item.asset_type}</p>
                              <p className="helper-text">Priority: {item.priority_weight}</p>
                            </>
                          )}
                          {type === "officers" && (
                            <>
                              <strong>{item.display_name}</strong>
                              <p>{item.username}</p>
                              <p className="helper-text">{item.ward}</p>
                              {item.departments && item.departments.length > 0 && <p className="helper-text">Departments: {item.departments.join(", ")}</p>}
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
                          {type !== "citizens" && type !== "jurisdictions" && (
                            <button type="button" className="secondary" onClick={() => handleEdit(item)}>Edit</button>
                          )}
                          <button type="button" className="danger" onClick={() => handleDelete(itemIdKey(item))}>Delete</button>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </>
          )}
        </div>
        {status && <p className="status-text" style={{ padding: "0.5rem 1rem", margin: 0 }}>{status}</p>}
      </div>
    </div>
  );
}

AdminManagerModal.propTypes = {
  type: PropTypes.oneOf(["officers", "departments", "citizens", "registry", "jurisdictions"]).isRequired,
  isOpen: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  authToken: PropTypes.string.isRequired,
  onRefresh: PropTypes.func
};

export default AdminManagerModal;
