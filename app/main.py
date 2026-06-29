from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
import os
import uuid
import datetime
import math

from .signals.signal1_llm import analyze_with_llm
from .signals.signal2_stylometric import analyze_with_stylometrics
from .audit import add_log_entry, get_log_entries

load_dotenv()

app = Flask(__name__)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["100 per 15 minutes", "500 per hour"],
    storage_uri="memory://"
)

def combine_signals(llm_score, stylometric_score, groq_available=True):
    """
    Combine two signals into a calibrated confidence score.
    Returns confidence score in [0, 1].
    """
    if groq_available:
        # Full mode: weighted average
        w1 = 0.55  # Groq LLM
        w2 = 0.45  # Stylometric
        
        raw_combined = (w1 * llm_score) + (w2 * stylometric_score)
        
        # If signals strongly disagree (> 0.4 difference), pull toward uncertain
        signal_diff = abs(llm_score - stylometric_score)
        if signal_diff > 0.4:
            raw_combined = 0.5 * raw_combined + 0.5 * 0.5
        
        # Asymmetry penalty: false positive (human labeled AI) is worse
        if raw_combined < 0.42:
            raw_penalized = raw_combined - 0.06
        else:
            raw_penalized = raw_combined
        
        # Sigmoid calibration
        midpoint = 0.5
        k = 6
        confidence = 1 / (1 + math.exp(-k * (raw_penalized - midpoint)))
        
    else:
        # Fallback mode: stylometric only, wider thresholds
        raw_penalized = stylometric_score
        midpoint = 0.5
        k = 4  # Less steep in fallback
        confidence = 1 / (1 + math.exp(-k * (raw_penalized - midpoint)))
    
    return max(0.0, min(1.0, confidence))

def get_label_and_attribution(confidence, fallback_mode=False):
    """
    Map confidence score to label category and text.
    """
    if fallback_mode:
        # Wider uncertain band in fallback
        low_threshold = 0.30
        high_threshold = 0.70
        disclaimer = " Assessment based on structural analysis only; semantic review unavailable."
    else:
        low_threshold = 0.35
        high_threshold = 0.65
        disclaimer = ""
    
    if confidence < low_threshold:
        attribution = "likely_ai"
        label = "This content was likely generated with AI assistance. The system detected consistent statistical patterns typical of language model output, including uniform sentence structure and repeated phrasing templates." + disclaimer
    elif confidence > high_threshold:
        attribution = "likely_human"
        label = "This content was likely written by a human author. The system detected natural variation in writing style, organic vocabulary choices, and thematic development consistent with human composition." + disclaimer
    else:
        attribution = "uncertain"
        label = "We cannot confidently determine whether this content was written by a human or generated with AI. The text shows mixed signals — some patterns suggest human authorship, others suggest AI assistance. The creator may submit an appeal if they believe this assessment is incorrect." + disclaimer
    
    return attribution, label

@app.route('/submit', methods=['POST'])
@limiter.limit("100 per 15 minutes")
def submit():
    data = request.get_json()
    
    if not data or 'text' not in data or 'creator_id' not in data:
        return jsonify({"error": "Missing required fields: text, creator_id"}), 400
    
    text = data['text']
    creator_id = data['creator_id']
    content_id = str(uuid.uuid4())
    
    # Signal 1: LLM-based classification
    try:
        llm_result = analyze_with_llm(text)
        llm_score = llm_result['score']
        groq_available = True
    except Exception as e:
        # Fallback if Groq fails
        llm_score = 0.5
        groq_available = False
    
    # Signal 2: Stylometric heuristics
    stylometric_result = analyze_with_stylometrics(text)
    stylometric_score = stylometric_result['score']
    
    # Combine signals
    confidence = combine_signals(llm_score, stylometric_score, groq_available)
    
    # Get label
    attribution, label = get_label_and_attribution(confidence, not groq_available)
    
    # Write to audit log
    log_entry = {
        "content_id": content_id,
        "creator_id": creator_id,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "attribution": attribution,
        "confidence": round(confidence, 3),
        "llm_score": round(llm_score, 3),
        "stylometric_score": round(stylometric_score, 3),
        "groq_available": groq_available,
        "status": "classified"
    }
    add_log_entry(log_entry)
    
    return jsonify({
        "content_id": content_id,
        "attribution": attribution,
        "confidence": round(confidence, 3),
        "llm_score": round(llm_score, 3),
        "stylometric_score": round(stylometric_score, 3),
        "label": label
    })

@app.route('/log', methods=['GET'])
def get_log():
    entries = get_log_entries()
    return jsonify({"entries": entries})

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)