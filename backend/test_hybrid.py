from app.services.classifier import HybridClassifier, ROADS_TRANSPORT, WATER_SANITATION, ELECTRICITY, GENERAL_REVIEWER

def test_classifier():
    print("Initializing classifier...")
    clf = HybridClassifier(confidence_threshold=0.70)
    
    # 1. Simple fast path
    t1 = "There are too many potholes on my street"
    r1 = clf.classify(t1)
    print(f"[{t1[:15]}...] -> {r1.department} (Conf: {r1.confidence:.2f}, Human: {r1.routed_to_human}, Entities: {r1.entities})")

    # 2. Hinglish fallback
    t2 = "street par bohot bada pothole hai, please theek kardo near Station"
    r2 = clf.classify(t2)
    print(f"[{t2[:15]}...] -> {r2.department} (Conf: {r2.confidence:.2f}, Human: {r2.routed_to_human}, Entities: {r2.entities})")

    # 3. Complete nonsense (should go to human reviewer)
    t3 = "The sky is blue and I want a sandwich near Central Park"
    r3 = clf.classify(t3)
    print(f"[{t3[:15]}...] -> {r3.department} (Conf: {r3.confidence:.2f}, Human: {r3.routed_to_human}, Entities: {r3.entities})")
    
    # 4. Feedback loop test
    # Let's use a very weird phrase that means "Roads"
    t4 = "the black tar is melting outside my house"
    r4_before = clf.classify(t4)
    print(f"BEFORE Retrain: [{t4[:15]}...] -> {r4_before.department} (Conf: {r4_before.confidence:.2f})")
    
    # Retrain
    clf.retrain(t4, ROADS_TRANSPORT)
    
    r4_after = clf.classify(t4)
    print(f"AFTER Retrain: [{t4[:15]}...] -> {r4_after.department} (Conf: {r4_after.confidence:.2f})")

if __name__ == "__main__":
    test_classifier()
