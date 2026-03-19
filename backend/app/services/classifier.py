from __future__ import annotations

from dataclasses import dataclass

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.naive_bayes import MultinomialNB
    from sklearn.pipeline import Pipeline

    SKLEARN_AVAILABLE = True
except Exception:
    SKLEARN_AVAILABLE = False
    Pipeline = None  # type: ignore[assignment]

ROADS_TRANSPORT = "Roads & Transport"
WATER_SANITATION = "Water & Sanitation"
ELECTRICITY = "Electricity"


@dataclass
class ClassificationResult:
    department: str
    confidence: float


class ComplaintClassifier:
    def __init__(self) -> None:
        self.pipeline = None
        if SKLEARN_AVAILABLE:
            self.pipeline = Pipeline(
                [
                    ("tfidf", TfidfVectorizer(ngram_range=(1, 2), stop_words="english")),
                    ("clf", MultinomialNB(alpha=0.2)),
                ]
            )
            self._fit_bootstrap_model()

    def _fit_bootstrap_model(self) -> None:
        samples = [
            ("Large potholes causing accidents on main road", ROADS_TRANSPORT),
            ("Broken traffic signal near metro station", ROADS_TRANSPORT),
            ("Bus stop shelter damaged and unsafe", ROADS_TRANSPORT),
            ("No drinking water supply in our lane", WATER_SANITATION),
            ("Sewage overflow creating foul smell", WATER_SANITATION),
            ("Garbage not collected for a week", WATER_SANITATION),
            ("Frequent power cuts in my area", ELECTRICITY),
            ("Transformer sparked and failed", ELECTRICITY),
            ("Streetlights not working at night", ELECTRICITY),
        ]

        x_train = [sample[0] for sample in samples]
        y_train = [sample[1] for sample in samples]
        self.pipeline.fit(x_train, y_train)

    def classify(self, text: str) -> ClassificationResult:
        clean_text = text.strip() or "general grievance"
        if not SKLEARN_AVAILABLE or self.pipeline is None:
            return self._classify_heuristic(clean_text)

        probabilities = self.pipeline.predict_proba([clean_text])[0]
        labels = self.pipeline.classes_

        best_idx = int(probabilities.argmax())
        return ClassificationResult(
            department=str(labels[best_idx]),
            confidence=float(probabilities[best_idx]),
        )

    def _classify_heuristic(self, text: str) -> ClassificationResult:
        lowered = text.lower()
        hints = {
            ROADS_TRANSPORT: ["pothole", "road", "traffic", "bus", "bridge", "signal"],
            WATER_SANITATION: ["water", "sewage", "drain", "garbage", "leak"],
            ELECTRICITY: ["electricity", "power", "streetlight", "transformer", "outage"],
        }

        best_department = ROADS_TRANSPORT
        best_score = -1
        for department, words in hints.items():
            score = sum(1 for word in words if word in lowered)
            if score > best_score:
                best_score = score
                best_department = department

        if best_score <= 0:
            return ClassificationResult(department="General Grievance", confidence=0.4)
        return ClassificationResult(department=best_department, confidence=min(0.92, 0.55 + best_score * 0.1))


classifier = ComplaintClassifier()
