from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
import os
import uuid
import datetime

from .signals.signal1_llm import analyze_with_llm
from .audit import add_log_entry, get_log_entries

load_dotenv()

app = Flask(__name__)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["100 per 15 minutes", "500 per hour"],
    storage_uri="memory://"
)

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
    llm_result = analyze_with_llm(text)
    llm_score = llm_result['score']
    
    # Placeholder for signal 2 and combined scoring
    # For now, use signal 1 score as placeholder confidence
    confidence = llm_score  # Will be replaced in M4
    
    # Placeholder label mapping (will be refined in M4/M5)
    if confidence < 0.35:
        attribution = "likely_ai"
        label = "This content was likely generated with AI assistance."
    elif confidence > 0.65:
        attribution = "likely_human"
        label = "This content was likely written by a human author."
    else:
        attribution = "uncertain"
        label = "We cannot confidently determine whether this content was written by a human or generated with AI."
    
    # Write to audit log
    log_entry = {
        "content_id": content_id,
        "creator_id": creator_id,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "attribution": attribution,
        "confidence": round(confidence, 2),
        "llm_score": round(llm_score, 2),
        "status": "classified"
    }
    add_log_entry(log_entry)
    
    return jsonify({
        "content_id": content_id,
        "attribution": attribution,
        "confidence": round(confidence, 2),
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