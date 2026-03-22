import { useState, useCallback } from "react";
import PropTypes from "prop-types";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:5000";

export function EscalateModal({ ticketId, isOpen, onClose, authToken, onRefresh }) {
    const [status, setStatus] = useState("");
    const [loading, setLoading] = useState(false);
    const [formData, setFormData] = useState({
        to_tier: "State",
        to_department: "",
        reason: "",
        transfer_type: "escalation"
    });

    const handleChange = (e) => {
        setFormData((prev) => ({ ...prev, [e.target.name]: e.target.value }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setStatus("Transferring ticket...");
        try {
            const response = await fetch(`${API_BASE}/api/complaints/${ticketId}/transfer`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${authToken}`
                },
                body: JSON.stringify(formData)
            });
            if (response.ok) {
                setStatus("Ticket transferred successfully.");
                setTimeout(() => {
                    onRefresh?.();
                    onClose();
                }, 1000);
            } else {
                const error = await response.json();
                setStatus(`Error: ${error.error || "Failed to transfer"}`);
            }
        } catch (error) {
            setStatus(`Error: ${error.message}`);
        } finally {
            setLoading(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
            <div className="modal-content" style={{ maxWidth: '400px' }}>
                <div className="modal-header">
                    <h3>Transfer / Escalate ({ticketId})</h3>
                    <button type="button" className="modal-close" onClick={onClose}>✕</button>
                </div>
                <div className="modal-body">
                    <form onSubmit={handleSubmit} className="form-grid" style={{ gridTemplateColumns: '1fr' }}>
                        <select name="transfer_type" value={formData.transfer_type} onChange={handleChange} style={{ padding: '0.7rem', borderRadius: '8px' }} required>
                            <option value="escalation">Escalate (Up)</option>
                            <option value="devolution">Devolve (Down)</option>
                            <option value="lateral">Lateral (Same Tier)</option>
                        </select>
                        <select name="to_tier" value={formData.to_tier} onChange={handleChange} style={{ padding: '0.7rem', borderRadius: '8px' }} required>
                            <option value="Local">Local</option>
                            <option value="State">State</option>
                            <option value="Central">Central</option>
                        </select>
                        <input type="text" name="to_department" placeholder="Destination Department (e.g. PWD)" value={formData.to_department} onChange={handleChange} required />
                        <textarea name="reason" placeholder="Reason for transfer (required by audit log)" value={formData.reason} onChange={handleChange} rows="3" required />
                        <div className="button-row" style={{ marginTop: '1rem' }}>
                            <button type="button" className="secondary" onClick={onClose} disabled={loading}>Cancel</button>
                            <button type="submit" disabled={loading}>{loading ? "Transferring..." : "Confirm Transfer"}</button>
                        </div>
                    </form>
                    {status && <p className="status-text">{status}</p>}
                </div>
            </div>
        </div>
    );
}

export function OwnershipModal({ ticketId, isOpen, onClose, authToken }) {
    const [status, setStatus] = useState("");
    const [loading, setLoading] = useState(false);
    const [stakes, setStakes] = useState([]);
    const [loadingStakes, setLoadingStakes] = useState(true);
    const [showAdd, setShowAdd] = useState(false);
    const [formData, setFormData] = useState({
        tier: "State",
        department_id: "",
        department_name: "",
        role: "secondary",
        share: 0.5
    });

    const fetchStakes = useCallback(async () => {
        try {
            const response = await fetch(`${API_BASE}/api/complaints/${ticketId}/ownership`, {
                headers: { Authorization: `Bearer ${authToken}` }
            });
            if (response.ok) {
                const payload = await response.json();
                setStakes(payload.stakes || []);
            }
        } catch {
            setStatus("Failed to load stakes.");
        } finally {
            setLoadingStakes(false);
        }
    }, [ticketId, authToken]);

    if (isOpen && loadingStakes) {
        fetchStakes();
    }

    const handleChange = (e) => {
        let val = e.target.value;
        if (e.target.name === "share") val = parseFloat(val) || 0;
        setFormData((prev) => ({ ...prev, [e.target.name]: val }));
    };

    const handleAdd = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            const response = await fetch(`${API_BASE}/api/complaints/${ticketId}/ownership`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${authToken}`
                },
                body: JSON.stringify(formData)
            });
            if (response.ok) {
                setStatus("Stake added successfully.");
                setShowAdd(false);
                setFormData({ tier: "State", department_id: "", department_name: "", role: "secondary", share: 0.5 });
                fetchStakes();
            } else {
                const error = await response.json();
                setStatus(`Error: ${error.error || "Failed to add stake"}`);
            }
        } catch (error) {
            setStatus(`Error: ${error.message}`);
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async (deptId) => {
        try {
            const response = await fetch(`${API_BASE}/api/complaints/${ticketId}/ownership/${deptId}`, {
                method: "DELETE",
                headers: { Authorization: `Bearer ${authToken}` }
            });
            if (response.ok) fetchStakes();
            else {
                const err = await response.json();
                alert(err.error || "Failed to delete");
            }
        } catch (err) {
            alert(err.message);
        }
    };

    const handleToggleSLA = async (deptId, currentShare, currentSLA) => {
        try {
            await fetch(`${API_BASE}/api/complaints/${ticketId}/ownership/${deptId}`, {
                method: "PUT",
                headers: { "Content-Type": "application/json", Authorization: `Bearer ${authToken}` },
                body: JSON.stringify({ share: currentShare, sla_owner: !currentSLA })
            });
            fetchStakes();
        } catch (err) {
            alert(err.message);
        }
    }

    if (!isOpen) return null;

    return (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
            <div className="modal-content" style={{ maxWidth: '500px' }}>
                <div className="modal-header">
                    <h3>Manage Ownership ({ticketId})</h3>
                    <button type="button" className="modal-close" onClick={onClose}>✕</button>
                </div>
                <div className="modal-body">
                    {loadingStakes ? <p>Loading stakes...</p> : (
                        <div className="manager-list">
                            {stakes.length === 0 && <p>No ownership stakes recorded.</p>}
                            {stakes.map(stake => (
                                <div key={stake.department_id} className="manager-item" style={{ alignItems: 'flex-start' }}>
                                    <div className="item-info">
                                        <strong>{stake.department_name}</strong>
                                        <div style={{ display: 'flex', gap: '0.4rem', marginTop: '0.3rem' }}>
                                            <span className={`badge tier-${stake.tier.toLowerCase()}`}>{stake.tier}</span>
                                            <span className="badge secondary">{stake.role}</span>
                                        </div>
                                        <p className="helper-text" style={{ marginTop: '0.4rem' }}>Share: {(stake.share * 100).toFixed(0)}%</p>
                                    </div>
                                    <div className="item-actions" style={{ flexDirection: 'column', gap: '0.3rem' }}>
                                        <button type="button" className="secondary" style={{ fontSize: '0.75rem', padding: '0.3rem 0.5rem' }} onClick={() => handleToggleSLA(stake.department_id, stake.share, stake.sla_owner)}>
                                            {stake.sla_owner ? "★ SLA Owner" : "Make SLA Owner"}
                                        </button>
                                        <button type="button" className="danger" style={{ fontSize: '0.75rem', padding: '0.3rem 0.5rem' }} onClick={() => handleDelete(stake.department_id)}>Remove</button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}

                    {showAdd ? (
                        <form onSubmit={handleAdd} className="form-grid" style={{ gridTemplateColumns: '1fr', marginTop: '1.5rem', background: 'color-mix(in srgb, var(--surface) 50%, transparent)', padding: '1rem', borderRadius: '8px' }}>
                            <h4>Add New Stake</h4>
                            <input type="text" name="department_id" placeholder="Dept ID (e.g. pwd_hr)" value={formData.department_id} onChange={handleChange} required />
                            <input type="text" name="department_name" placeholder="Dept Name (e.g. PWD Haryana)" value={formData.department_name} onChange={handleChange} required />
                            <select name="tier" value={formData.tier} onChange={handleChange} style={{ padding: '0.7rem' }}>
                                <option value="Local">Local</option>
                                <option value="State">State</option>
                                <option value="Central">Central</option>
                            </select>
                            <select name="role" value={formData.role} onChange={handleChange} style={{ padding: '0.7rem' }}>
                                <option value="primary">Primary</option>
                                <option value="secondary">Secondary</option>
                                <option value="observer">Observer</option>
                            </select>
                            <input type="number" step="0.1" max="1.0" min="0.0" name="share" placeholder="Share (0.0 to 1.0)" value={formData.share} onChange={handleChange} required />
                            <div className="button-row">
                                <button type="button" className="secondary" onClick={() => setShowAdd(false)}>Cancel</button>
                                <button type="submit" disabled={loading}>Save Stake</button>
                            </div>
                        </form>
                    ) : (
                        <button type="button" className="secondary" style={{ marginTop: '1rem', width: '100%' }} onClick={() => setShowAdd(true)}>+ Add Department Stake</button>
                    )}

                    {status && <p className="status-text">{status}</p>}
                </div>
            </div>
        </div>
    );
}

EscalateModal.propTypes = {
    ticketId: PropTypes.string.isRequired,
    isOpen: PropTypes.bool.isRequired,
    onClose: PropTypes.func.isRequired,
    authToken: PropTypes.string.isRequired,
    onRefresh: PropTypes.func
};

OwnershipModal.propTypes = {
    ticketId: PropTypes.string.isRequired,
    isOpen: PropTypes.bool.isRequired,
    onClose: PropTypes.func.isRequired,
    authToken: PropTypes.string.isRequired
};
