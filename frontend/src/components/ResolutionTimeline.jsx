import PropTypes from "prop-types";

const TIMELINE_STEPS = [
  "Complaint Registered",
  "AI Categorization",
  "Geo Routing",
  "Field Action",
  "Issue Resolved"
];

function ResolutionTimeline({ currentStep = 2 }) {
  return (
    <section className="card">
      <h3>Resolution Timeline</h3>
      <div className="timeline">
        {TIMELINE_STEPS.map((step, index) => {
          const isDone = index <= currentStep;
          return (
            <div key={step} className={`timeline-item ${isDone ? "done" : "pending"}`}>
              <div className="timeline-dot" />
              <div>
                <p>{step}</p>
                <small>{isDone ? "Completed" : "Awaiting"}</small>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

ResolutionTimeline.propTypes = {
  currentStep: PropTypes.number
};

export default ResolutionTimeline;
