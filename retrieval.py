"""Unicode lexical retrieval over curated bilingual evidence, with optional local E5 vectors.
Scores are ranking signals, never eligibility or confidence probabilities.
"""
import re, unicodedata, math
from catalog import source_current

def tokens(text):
    text = ''.join(c for c in unicodedata.normalize('NFKD', text.casefold()) if not unicodedata.combining(c))
    return set(re.findall(r'[^\W_]+', text, re.UNICODE))

def search_knowledge(catalog, query, topics=None, locale='en', limit=8, as_of=None):
    query_tokens = tokens(query)
    sources = {s['id']: s for s in catalog['sources']}
    scored = []
    for c in catalog['chunks']:
        if topics and c['topic'] not in topics:
            continue
        s = sources[c['source_id']]
        if not source_current(s, as_of):
            continue
        terms = tokens(' '.join(c['text'].values()) + ' ' + ' '.join(c.get('keywords', [])) + ' ' + s['title'])
        overlap = len(query_tokens & terms)
        score = overlap / math.sqrt(max(1, len(terms))) + (1 if topics and c['topic'] in topics else 0)
        if score > 0:
            scored.append((score, c['id'], dict(c, display_text=c['text'][locale], url=s['url'], source_version=s['version'])))
    return [c for _, _, c in sorted(scored, key=lambda v: (-v[0], v[1]))[:limit]]
