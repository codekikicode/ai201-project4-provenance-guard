import json
import os

LOG_FILE = os.path.join(os.path.dirname(__file__), '..', 'audit_log.jsonl')

def add_log_entry(entry):
    """Append a structured entry to the audit log (JSON Lines format)."""
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry) + '\n')

def get_log_entries(limit=50):
    """Return the most recent log entries as a list of dicts."""
    if not os.path.exists(LOG_FILE):
        return []
    
    entries = []
    with open(LOG_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    
    # Return most recent first, limited to `limit` entries
    return entries[-limit:][::-1]