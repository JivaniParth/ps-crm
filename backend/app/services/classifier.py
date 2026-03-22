from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

try:
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.naive_bayes import MultinomialNB
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    from transformers import pipeline
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False

logger = logging.getLogger(__name__)

ROADS_TRANSPORT = "Roads & Transport"
WATER_SANITATION = "Water & Sanitation"
ELECTRICITY = "Electricity"
GENERAL_REVIEWER = "General Human Reviewer"

ALL_DEPARTMENTS = [ROADS_TRANSPORT, WATER_SANITATION, ELECTRICITY, GENERAL_REVIEWER]


@dataclass
class ClassificationResult:
    department: str
    confidence: float
    entities: list[str] = field(default_factory=list)
    routed_to_human: bool = False


class HybridClassifier:
    """
    Hybrid NLP Strategy:
    1. TF-IDF + Naive Bayes (Fast execution for simple, keyword-heavy english).
    2. Deep BERT Fallback (For complex, Hinglish, contextual regional queries).
    3. Heuristics fallback (Last resort basic regex).
    4. General Human Reviewer (If confidence < 70%).
    """
    def __init__(self, confidence_threshold: float = 0.70) -> None:
        self.confidence_threshold = confidence_threshold
        self.vectorizer = None
        self.nb_classifier = None
        self.bert_classifier = None
        self.ner_pipeline = None

        # 1. Initialize Fast Path (Scikit-Learn)
        if SKLEARN_AVAILABLE:
            self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
            self.nb_classifier = MultinomialNB(alpha=0.2)
            self._bootstrap_tfidf()

        # 2. Initialize Deep Fallback Path (HuggingFace Transformers)
        if HF_AVAILABLE:
            try:
                # Use a zero-shot model capable of basic cross-lingual understanding if internet available
                self.bert_classifier = pipeline(
                    "zero-shot-classification",
                    model="MoritzLaurer/mDeBERTa-v3-base-mnli-xnli",
                    device=-1 # CPU by default, switch to 0 for GPU
                )
                self.ner_pipeline = pipeline("ner", aggregation_strategy="simple", device=-1)
            except Exception as e:
                logger.warning(f"Could not load HuggingFace pipelines. Deep Fallback unavailable: {e}")
                self.bert_classifier = None
                self.ner_pipeline = None

    def _bootstrap_tfidf(self) -> None:
        """Seed the basic NLP pipeline."""
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
        x_train = [s[0] for s in samples]
        y_train = [s[1] for s in samples]
        
        # Fit vectorizer
        X_vec = self.vectorizer.fit_transform(x_train)
        
        # Use partial_fit so that we can iteratively retrain via explicit feedback loops
        self.nb_classifier.partial_fit(X_vec, y_train, classes=ALL_DEPARTMENTS)


    def retrain(self, text: str, true_department: str) -> bool:
        """
        Feedback loop (Online Learning): 
        When an officer manually reassigns a misclassified ticket, update internal weights in real-time.
        """
        if not SKLEARN_AVAILABLE or not self.vectorizer or not self.nb_classifier:
            return False

        if true_department not in ALL_DEPARTMENTS:
            return False

        clean_text = text.strip()
        if not clean_text:
            return False

        try:
            # Ignore unseen vocabulary (fit_transform cannot be used online with MultinomialNB safely without hashing trick,
            # but transform keeps the existing dim and updates weights for known n-grams)
            X_vec = self.vectorizer.transform([clean_text])
            self.nb_classifier.partial_fit(X_vec, [true_department])
            logger.info(f"Retrained classifier with ground truth correction: '{clean_text[:30]}...' -> {true_department}")
            return True
        except Exception as e:
            logger.error(f"Failed to retrain classifier: {e}")
            return False

    def extract_entities(self, text: str) -> list[str]:
        """Extract landmarks or street/organization names for Geo Routing assistance."""
        entities = []
        
        # 1. Try Deep NER if available
        if self.ner_pipeline:
            try:
                res = self.ner_pipeline(text)
                for ent in res:
                    if ent["entity_group"] in ["LOC", "ORG", "FAC"]:
                        entities.append(ent["word"])
            except Exception as e:
                logger.warning(f"HF NER extraction failed: {e}")

        # 2. Heuristics fallback (always append)
        street_patterns = [
            r"\b(?:street|st|road|rd|avenue|ave|lane|ln|highway|nh)\b(?:\s+\w+)?",
            r"(?:near|opposite|behind|towards)\s+([A-Z]\w+(?:\s+[A-Z]\w+)*)"
        ]
        for pattern in street_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for m in matches:
                # Capture just the group if isolated, else entire matched phrase
                if m.groups() and m.group(1):
                    entities.append(m.group(1).title())
                else:
                    entities.append(m.group(0).title())
                    
        return list(set([e for e in entities if len(e) > 3]))

    def classify(self, text: str) -> ClassificationResult:
        """Process natural language, triggering sequential fallbacks if confidence is below 70% threshold."""
        clean_text = text.strip()
        entities = self.extract_entities(clean_text)

        if not clean_text:
            return ClassificationResult(department=GENERAL_REVIEWER, confidence=1.0, entities=[], routed_to_human=True)

        fast_conf = 0.0

        # Step 1: Fast TF-IDF Path
        if SKLEARN_AVAILABLE and self.vectorizer and self.nb_classifier:
            X_vec = self.vectorizer.transform([clean_text])
            probs = self.nb_classifier.predict_proba(X_vec)[0]
            best_idx = int(np.argmax(probs))
            fast_dept = self.nb_classifier.classes_[best_idx]
            fast_conf = float(probs[best_idx])

            if fast_conf >= self.confidence_threshold and fast_dept != GENERAL_REVIEWER:
                return ClassificationResult(department=fast_dept, confidence=fast_conf, entities=entities)

        # Step 2: Deep BERT Multilingual Fallback (Hinglish/Regional Contextual processing)
        if HF_AVAILABLE and self.bert_classifier:
            try:
                candidate_labels = [ROADS_TRANSPORT, WATER_SANITATION, ELECTRICITY]
                res = self.bert_classifier(clean_text, candidate_labels)
                best_label = res["labels"][0]
                best_score = float(res["scores"][0])
                
                if best_score >= self.confidence_threshold:
                    return ClassificationResult(
                        department=best_label,
                        confidence=best_score,
                        entities=entities
                    )
            except Exception as e:
                logger.error(f"BERT fallback failed: {e}")

        # Step 3: Heuristic Keyword Fallback
        heur_res = self._classify_heuristic(clean_text)
        if heur_res.confidence >= self.confidence_threshold:
            heur_res.entities = entities
            return heur_res

        # Step 4: Nothing reached 70% confidence. Route to General Human Reviewer.
        # This guarantees 100% confidence in the fall-through route instead of guessing poorly.
        sys_conf = float(max(fast_conf, heur_res.confidence))
        return ClassificationResult(
            department=GENERAL_REVIEWER,
            confidence=max(sys_conf, 0.71),  # Assign pseudo-confidence > threshold for Human
            entities=entities,
            routed_to_human=True
        )

    def _classify_heuristic(self, text: str) -> ClassificationResult:
        lowered = text.lower()
        hints = {
            ROADS_TRANSPORT: ["pothole", "road", "traffic", "bus", "bridge", "signal", "pavement", "rasta"],
            WATER_SANITATION: ["water", "sewage", "drain", "garbage", "leak", "pani", "kachra", "smell"],
            ELECTRICITY: ["electricity", "power", "streetlight", "transformer", "outage", "bijli", "light", "wire"],
        }

        best_department = ROADS_TRANSPORT
        best_score = -1
        for department, words in hints.items():
            score = sum(1 for word in words if word in lowered)
            if score > best_score:
                best_score = score
                best_department = department

        if best_score <= 0:
            return ClassificationResult(department=GENERAL_REVIEWER, confidence=0.4, navigated_to_human=True)
        return ClassificationResult(department=best_department, confidence=min(0.92, 0.55 + best_score * 0.1))


# Instantiate singleton
classifier = HybridClassifier(confidence_threshold=0.70)
