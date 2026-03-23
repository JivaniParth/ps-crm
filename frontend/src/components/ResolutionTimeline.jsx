import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:5000";

function ResolutionTimeline({ currentStep = 0, ticket = null }) {
  const [nudgeStatus, setNudgeStatus] = useState({ canNudge: false, message: "Active after 24 hours of inactivity" });
  const [timelineEvents, setTimelineEvents] = useState([]);

  useEffect(() => {
    if (!ticket) return;

    // Check if 24 hours have passed since the last update
    const lastUpdate = new Date(ticket.updated_at || ticket.created_at);
    const now = new Date();
    const hoursSinceUpdate = (now - lastUpdate) / (1000 * 60 * 60);

    if (hoursSinceUpdate >= 24) {
      setNudgeStatus({ canNudge: true, message: "Push to Nudge" });
    } else {
      setNudgeStatus({ canNudge: false, message: "Nudge available in " + Math.ceil(24 - hoursSinceUpdate) + " hours" });
    }

    const fetchTimeline = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/complaints/${ticket.ticket_id}/timeline`);
        if (res.ok) {
          const data = await res.json();
          const mapped = data.steps.map(step => ({
            label: `Transferred: ${step.from_tier} → ${step.to_tier}`,
            detail: step.reason,
            timestamp: step.timestamp
          }));

          setTimelineEvents([
            { label: "Submitted", detail: "Grievance logged securely.", timestamp: ticket.created_at },
            ...mapped,
            ...(ticket.status === "Resolved" ? [{ label: "Resolved", detail: "The issue has been resolved.", timestamp: ticket.resolved_at || ticket.updated_at }] : [])
          ]);
        }
      } catch (err) {
        console.error("Timeline fetch error:", err);
      }
    };
    fetchTimeline();

  }, [ticket, currentStep]);

  const handleNudge = async () => {
    if (!nudgeStatus.canNudge) return;
    setNudgeStatus({ canNudge: false, message: "Nudge Sent! Authority notified." });
    // In a real app, this would trigger an API call to /api/complaints/:id/nudge
  };

  return (
    <section className="card resolution-journey">
      <div className="journey-header">
        <h3>Resolution Journey</h3>
        {ticket && currentStep < 4 && (
          <button
            className={`nudge-btn ${nudgeStatus.canNudge ? "active" : "disabled"}`}
            onClick={handleNudge}
            disabled={!nudgeStatus.canNudge}
            title={nudgeStatus.message}
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 17a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V9.5C2 7 4 5 6.5 5h4.63c.11 0 .23-.02.34-.06l4.42-1.77a2 2 0 0 1 2.61 2.36V7h1.5A2.5 2.5 0 0 1 22 9.5z" /><path d="m14 16 1.74-2.61a2 2 0 0 0-.74-2.82l-2.02-1.15a2 2 0 0 0-2.82.74L8.5 13" /></svg>
            {nudgeStatus.message}
          </button>
        )}
      </div>

      <div className="timeline-rich">
        {timelineEvents.map((step, index) => {
          const isDone = index < timelineEvents.length - 1 || ticket.status === "Resolved";
          const isActive = index === timelineEvents.length - 1 && ticket.status !== "Resolved";
          const isPending = false;

          let statusClass = isDone ? "done" : isActive ? "active" : "pending";

          return (
            <div key={step.label} className={`timeline-item-rich ${statusClass}`}>
              <div className="timeline-indicator">
                <div className="timeline-node">
                  {isDone ? (
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                  ) : isActive ? (
                    <div className="pulse-dot"></div>
                  ) : null}
                </div>
                {index < timelineEvents.length - 1 && <div className="timeline-connector"></div>}
              </div>

              <div className="timeline-content">
                <h4 className="step-title">{step.label}</h4>

                {/* Micro-copy for the active step */}
                {(isActive || isDone) && (
                  <div className="step-microcopy">
                    <p className="detail-text">{step.detail}</p>
                    {step.timestamp && <p className="detail-text" style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{new Date(step.timestamp).toLocaleString()}</p>}

                    {/* Show Officer Details contextually */}
                    {isActive && ticket && ticket.assigned_officer && (
                      <div className="officer-card">
                        <div className="officer-avatar">
                          {ticket.assigned_officer.charAt(0).toUpperCase()}
                        </div>
                        <div className="officer-info">
                          <span className="officer-role">Assigned Field Officer</span>
                          <span className="officer-name">{ticket.assigned_officer}</span>
                          <span className="officer-contact">📞 +91 98XXX XXXXX • {ticket.ward || "Ward"}</span>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {isDone && <span className="step-completed-text">Completed</span>}
                {isPending && <span className="step-pending-text">Upcoming</span>}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

ResolutionTimeline.propTypes = {
  currentStep: PropTypes.number,
  ticket: PropTypes.object
};

export default ResolutionTimeline;
