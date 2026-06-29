import re
import math

# AI transition phrases that indicate templated structure
AI_TRANSITIONS = [
    'furthermore', 'moreover', 'in conclusion', 'it is important to note',
    'it is essential to', 'it is equally essential', 'stakeholders must',
    'various sectors', 'responsible deployment', 'transformative paradigm',
    'optimal results', 'best practices', 'aforementioned', 'leverage',
    'holistic approach', 'moving forward', 'going forward', 'at the end of the day',
    'in order to', 'due to the fact that', 'in the event that'
]

def analyze_with_stylometrics(text):
    """
    Signal 2: Stylometric heuristics (pure Python, no external APIs).
    Returns a dict with 'score' (float 0-1) and 'metrics' (dict).
    Higher score = more human-like.
    """
    if not text or len(text.strip()) == 0:
        return {"score": 0.5, "metrics": {}, "reasoning": "Empty text"}
    
    # Clean and split into sentences
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    if len(sentences) == 0:
        return {"score": 0.5, "metrics": {}, "reasoning": "No sentences found"}
    
    words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
    if len(words) == 0:
        return {"score": 0.5, "metrics": {}, "reasoning": "No words found"}
    
    # --- Metric 1: Sentence length variance (coefficient of variation) ---
    sentence_lengths = [len(s.split()) for s in sentences]
    mean_length = sum(sentence_lengths) / len(sentence_lengths)
    
    if len(sentence_lengths) > 1 and mean_length > 0:
        variance = sum((x - mean_length) ** 2 for x in sentence_lengths) / (len(sentence_lengths) - 1)
        std_dev = math.sqrt(variance)
        cv = std_dev / mean_length
    else:
        cv = 0
    
    # AI text typically has CV < 0.25, human > 0.35
    # Score: 0 = very uniform (AI), 1 = very variable (human)
    if cv < 0.15:
        sentence_variance_score = 0.0
    elif cv > 0.5:
        sentence_variance_score = 1.0
    else:
        sentence_variance_score = (cv - 0.15) / 0.35
    
    # --- Metric 2: Type-Token Ratio (with adjustment for text length) ---
    unique_words = set(words)
    ttr = len(unique_words) / len(words)
    
    # MATTR (Moving Average TTR) is better, but simple TTR with length correction:
    # Short texts naturally have high TTR, long texts lower
    # Use a correction factor
    expected_ttr = 0.8 / (len(words) ** 0.1)  # Empirical approximation
    ttr_deviation = ttr - expected_ttr
    
    # AI often has slightly higher TTR due to avoiding repetition
    # Human has more personal idiolect (repeated favorite words)
    ttr_score = max(0.0, min(1.0, 0.5 - ttr_deviation * 2))
    
    # --- Metric 3: AI transition phrase density ---
    text_lower = text.lower()
    transition_count = sum(1 for phrase in AI_TRANSITIONS if phrase in text_lower)
    transition_density = transition_count / len(sentences) if sentences else 0
    
    # High density = very AI-like
    if transition_density >= 0.5:
        transition_score = 0.0
    elif transition_density == 0:
        transition_score = 1.0
    else:
        transition_score = 1.0 - (transition_density / 0.5)
    
    # --- Metric 4: Punctuation idiosyncrasy ---
    punct_count = sum(1 for c in text if c in '.,;:!?-—')
    punct_density = punct_count / len(text) if len(text) > 0 else 0
    
    # AI tends toward ~0.08-0.12, humans vary more
    # Score higher for being outside the "AI sweet spot"
    ai_sweet_spot = 0.10
    deviation = abs(punct_density - ai_sweet_spot)
    punct_score = min(1.0, deviation / 0.08)
    
    # --- Metric 5: First-person and emotional markers (human indicators) ---
    human_markers = ['i ', 'me ', 'my ', 'honestly', 'literally', 'like ', 'way too',
                     'probably', 'maybe', 'idk', 'tbh', 'tbh', 'tbh', 'kinda', 'sorta',
                     'whatever', 'ugh', 'omg', 'wow', 'actually', 'really', 'so ', 'too ']
    marker_count = sum(1 for marker in human_markers if marker in text_lower)
    marker_density = marker_count / len(words) if words else 0
    
    # Higher density = more human
    marker_score = min(1.0, marker_density * 20)
    
    # --- Combine metrics with adjusted weights ---
    weights = {
        'sentence_variance': 0.25,
        'ttr': 0.15,
        'transitions': 0.30,  # Increased — strong AI indicator
        'punctuation': 0.15,
        'markers': 0.15
    }
    
    combined_score = (
        weights['sentence_variance'] * sentence_variance_score +
        weights['ttr'] * ttr_score +
        weights['transitions'] * transition_score +
        weights['punctuation'] * punct_score +
        weights['markers'] * marker_score
    )
    
    # Clamp to [0, 1]
    combined_score = max(0.0, min(1.0, combined_score))
    
    return {
        "score": round(combined_score, 3),
        "metrics": {
            "sentence_variance_score": round(sentence_variance_score, 3),
            "cv": round(cv, 3),
            "ttr": round(ttr, 3),
            "ttr_score": round(ttr_score, 3),
            "transition_density": round(transition_density, 3),
            "transition_score": round(transition_score, 3),
            "punct_density": round(punct_density, 3),
            "punct_score": round(punct_score, 3),
            "marker_density": round(marker_density, 3),
            "marker_score": round(marker_score, 3),
            "sentence_count": len(sentences),
            "word_count": len(words)
        },
        "reasoning": f"SV={sentence_variance_score:.2f}, TTR={ttr_score:.2f}, Trans={transition_score:.2f}, Punct={punct_score:.2f}, Markers={marker_score:.2f}"
    }