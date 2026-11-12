"""Curated preparation catalog. Relevance is never an eligibility outcome."""
import json
from pathlib import Path
from datetime import datetime, date
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent

def bc_today():
    return datetime.now(ZoneInfo('America/Vancouver')).date().isoformat()

def load_catalog():
    return json.loads((ROOT / 'data/catalog/navigation.json').read_text(encoding='utf-8'))

def fact_value(profile, field):
    f = profile.get('facts', {}).get(field, {})
    return f.get('value', 'unknown') if f.get('state') == 'confirmed' else 'unknown'

def available_programs(catalog, profile):
    goals = profile.get('goals', [])
    school = fact_value(profile, 'institution')
    province = fact_value(profile, 'province')
    records = []
    for p in catalog['programs']:
        if p['topic'] not in goals:
            continue
        if p.get('institutions') and school not in p['institutions']:
            continue
        if p.get('unknown_institution') and school in ('sfu', 'ubc_vancouver'):
            continue
        if p.get('requires_children') and fact_value(profile, 'children') == 'no':
            continue
        if province == 'other' and p.get('jurisdiction') == 'BC':
            continue
        records.append(p)
    priority = profile.get('priority')
    return sorted(records, key=lambda p: (p['topic'] != priority, goals.index(p['topic'])))

def source_current(source, as_of=None):
    try:
        age = (date.fromisoformat(as_of or bc_today()) - date.fromisoformat(source['checked_on'])).days
        return source.get('status') == 'available' and 0 <= age <= source.get('freshness_days', 30)
    except (KeyError, ValueError):
        return False
