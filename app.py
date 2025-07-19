from flask import Flask, request, jsonify ,send_from_directory
import spacy
import pandas as pd
from rapidfuzz import process

app = Flask(__name__)
@app.route('/')
def index():
    return send_from_directory('static', 'INDEX.html')


# Load spaCy English model (make sure to install: python -m spacy download en_core_web_sm)
nlp = spacy.load("en_core_web_sm")

# Example canonical data (replace with your full dataset or CSV loads)
cities = pd.DataFrame({
    "canonical_name": ["new delhi", "ahmedabad", "chennai"],
    "aliases": ["delhi", "ahmedabad", "madras"]
})
states = pd.DataFrame({
    "canonical_name": ["maharashtra", "tamil nadu"],
    "aliases": ["maharastra", "tn"]
})
countries = pd.DataFrame({
    "canonical_name": ["india", "new zealand"],
    "aliases": ["bharat", "nz"]
})

# Create a unified lookup list with category info
def build_lookup():
    lookup = []
    for _, row in cities.iterrows():
        names = [row['canonical_name']] + row['aliases'].split(",") if row['aliases'] else [row['canonical_name']]
        for name in names:
            lookup.append(("City", name.strip().lower(), row['canonical_name']))
    for _, row in states.iterrows():
        names = [row['canonical_name']] + row['aliases'].split(",") if row['aliases'] else [row['canonical_name']]
        for name in names:
            lookup.append(("State", name.strip().lower(), row['canonical_name']))
    for _, row in countries.iterrows():
        names = [row['canonical_name']] + row['aliases'].split(",") if row['aliases'] else [row['canonical_name']]
        for name in names:
            lookup.append(("Country", name.strip().lower(), row['canonical_name']))
    return lookup

lookup_table = build_lookup()

def fuzzy_search(token):
    # Search token against all names in lookup_table with rapidfuzz
    choices = [item[1] for item in lookup_table]
    match = process.extractOne(token.lower(), choices, score_cutoff=75)
    if match:
        idx = choices.index(match[0])
        return {
            "type": lookup_table[idx][0],
            "canonical": lookup_table[idx][2],
            "score": match[1]
        }
    return None

@app.route('/extract_places', methods=['POST'])
def extract_places():
    data = request.get_json()
    query = data.get('query', '')
    if not query:
        return jsonify([])

    doc = nlp(query)
    # Extract GPE (geo-political entity) entities
    tokens = [ent.text for ent in doc.ents if ent.label_ == "GPE"]
    print("Extracted GPE tokens:", tokens)

    # Fallback: if no GPEs found, try all unique words in the query
    if not tokens:
        tokens = list(set([token.text for token in doc if token.is_alpha]))

    results = []
    for token in tokens:
        match = fuzzy_search(token)
        if match:
            results.append({
                "token": token,
                "canonical": match['canonical'],
                "type": match['type']
            })
    return jsonify(results)

if __name__ == '__main__':
    print("Flask app is starting...")
    app.run(debug=True)
