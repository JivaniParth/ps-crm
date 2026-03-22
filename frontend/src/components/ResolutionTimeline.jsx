import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";

const TIMELINE_STEPS = [
  { label: "Submitted", detail: "Your grievance has been securely logged in the system." },
  { label: "AI Classified", detail: "Our AI model has accurately routed this to the correct department." },
  { label: "Officer Assigned", detail: "An official is reviewing the location and requirements." },
  { label: "Field Work Started", detail: "Awaiting spare parts from the central warehouse." },
  { label: "Resolved", detail: "The issue has been resolved successfully." }
];

function ResolutionTimeline({ currentStep = 0, ticket = null }) {
  const [nudgeStatus, setNudgeStatus] = useState({ canNudge: false, message: "Active after 24 hours of inactivity" });

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

    // For demo purposes, if it's not resolved, we could allow nudge testing, but we'll stick to the actual logic.
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
        {TIMELINE_STEPS.map((step, index) => {
          const isDone = index < currentStep;
          const isActive = index === currentStep;
          const isPending = index > currentStep;

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
                {index < TIMELINE_STEPS.length - 1 && <div className="timeline-connector"></div>}
              </div>

              <div className="timeline-content">
                <h4 className="step-title">{step.label}</h4>

                {/* Micro-copy for the active step */}
                {isActive && (
                  <div className="step-microcopy">
                    <p className="detail-text">{step.detail}</p>

                    {/* Show Officer Details if past the 'AI Classified' step (index >= 2) */}
                    {index >= 2 && ticket && ticket.assigned_officer && (
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
