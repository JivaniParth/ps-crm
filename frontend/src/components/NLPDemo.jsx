import { useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:5000";

const DEPARTMENT_HINTS = {
  "Roads & Transport": ["pothole", "road", "bus", "traffic", "bridge"],
  "Water & Sanitation": ["water", "sewage", "drain", "leak", "garbage"],
  Electricity: ["electricity", "power", "transformer", "outage", "wire"]
};

function heuristicClassify(text) {
  const sample = text.toLowerCase();
  const scores = Object.entries(DEPARTMENT_HINTS).map(([department, words]) => ({
    department,
    score: words.reduce((acc, token) => acc + (sample.includes(token) ? 1 : 0), 0)
  }));

  scores.sort((a, b) => b.score - a.score);
  const winner = scores[0];
  return {
    department: winner.score === 0 ? "General Grievance" : winner.department,
    confidence: winner.score === 0 ? 0.4 : Math.min(0.95, 0.55 + winner.score * 0.12)
  };
}

function NLPDemo({ onPrediction }) {
  const [text, setText] = useState("");
  const [liveResult, setLiveResult] = useState({ department: "General Grievance", confidence: 0.4 });

  const result = useMemo(() => heuristicClassify(text), [text]);

  useEffect(() => {
    const controller = new AbortController();
    const timeout = setTimeout(async () => {
      const trimmed = text.trim();
      if (!trimmed) {
        setLiveResult({ department: "General Grievance", confidence: 0.4 });
        onPrediction({ department: "General Grievance", confidence: 0.4 });
        return;
      }

      try {
        const response = await fetch(`${API_BASE}/api/classify`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: trimmed }),
          signal: controller.signal
        });

        if (!response.ok) {
          throw new Error("classification request failed");
        }

        const payload = await response.json();
        const prediction = {
          department: payload.department,
          confidence: payload.confidence
        };
        setLiveResult(prediction);
        onPrediction(prediction);
      } catch {
        const fallback = heuristicClassify(trimmed);
        setLiveResult(fallback);
        onPrediction(fallback);
      }
    }, 300);

    return () => {
      clearTimeout(timeout);
      controller.abort();
    };
  }, [text, onPrediction]);

  const handleChange = (event) => {
    const value = event.target.value;
    setText(value);
  };

  return (
    <section className="card">
      <h3>Live NLP Classifier</h3>
      <p>Type your complaint to see real-time department categorization.</p>
      <textarea
        rows={5}
        value={text}
        onChange={handleChange}
        placeholder="Streetlights near Sector 14 are non-functional for 5 days..."
      />
      <div className="prediction-row">
        <span className="badge">{liveResult.department || result.department}</span>
        <span>{Math.round((liveResult.confidence || result.confidence) * 100)}% confidence</span>
      </div>
    </section>
  );
}

NLPDemo.propTypes = {
  onPrediction: PropTypes.func.isRequired
};

export default NLPDemo;
