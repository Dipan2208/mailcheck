import re
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, jsonify, render_template, request
import verifier

app = Flask(__name__)
MAX_ADDRESSES = 100


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/status")
def status():
    return jsonify(smtp=verifier.smtp_available())


@app.post("/api/check")
def check():
    raw = (request.get_json(silent=True) or {}).get("emails", "")
    seen, emails = set(), []
    for e in re.split(r"[\s,;]+", raw):
        if e and e.lower() not in seen:
            seen.add(e.lower())
            emails.append(e)
    if not emails:
        return jsonify(error="Paste at least one address."), 400
    if len(emails) > MAX_ADDRESSES:
        return jsonify(error=f"Limit is {MAX_ADDRESSES} addresses per run."), 400
    with ThreadPoolExecutor(8) as pool:
        results = list(pool.map(verifier.check, emails))
    return jsonify(results=results, smtp=verifier.smtp_available())


if __name__ == "__main__":
    app.run(debug=True)
