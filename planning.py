"""Correction-aware preparation plans with stable IDs and explicit source dependencies."""
from copy import deepcopy
from catalog import available_programs, fact_value, source_current, bc_today
from api_contracts import PortablePlan

def build_plan(catalog, profile, locale='en', previous=None, profile_version=0, as_of=None):
    previous = previous or {}
    as_of = as_of or bc_today()
    sources = {s['id']: s for s in catalog['sources']}
    old = {t['id']: t for t in previous.get('tasks', [])}
    old_enquiries = {e['program_id']: e for e in previous.get('enquiries', [])}
    tasks, enquiries, versions = [], [], {}
    for p in available_programs(catalog, profile):
        deps = p['dependencies']
        values = {f: fact_value(profile, f) for f in deps}
        src = {sid: sources[sid]['version'] for sid in p['sources']}
        versions.update(src)
        stale = any(not source_current(sources[sid], as_of) for sid in src)
        for step in p['steps']:
            tid = p['id'] + '.' + step['id']
            prior = old.get(tid)
            reason = 'source_stale' if stale else (prior.get('review_reason') if prior else None)
            if prior and prior['source_versions'] != src:
                reason = 'source_changed'
            elif prior and prior['dependency_values'] != values:
                reason = 'facts_changed'
            readiness = 'stale' if reason else ('needs_information' if any(values[f] == 'unknown' for f in step.get('requires', [])) else step.get('readiness', 'needs_official_confirmation'))
            variant = step.get('variants', {})
            text = variant.get('values', {}).get(values.get(variant.get('field')), step['text'])[locale]
            t = dict(id=tid, program_id=p['id'], topic=p['topic'], group=step['group'], text=text,
                     destination=step.get('url', p['url']), evidence=step.get('sources', p['sources']),
                     dependencies=deps, dependency_values=values, source_versions=src,
                     readiness=readiness, completion=prior.get('completion', 'todo') if prior else 'todo',
                     user_text=prior.get('user_text') if prior else None, review_reason=reason, due_date=None)
            if reason and t['completion'] == 'done':
                t['completion'] = 'todo'
            tasks.append(t)
        prior = old_enquiries.get(p['id'])
        context = '\n'.join(f"{catalog['profile_labels'][locale][f]}: {catalog['profile_values'][locale].get(v, v)}" for f, v in values.items())
        e = dict(program_id=p['id'], text=p['enquiry'][locale] + ('\n\n' + context if context else ''), user_text=prior.get('user_text') if prior else None,
                 dependencies=deps, dependency_values=values, source_versions=src,
                 needs_review=stale or bool(prior and (prior.get('needs_review') or prior['dependency_values'] != values or prior['source_versions'] != src)))
        enquiries.append(e)
    # Preserve edited or completed work removed by a correction, visibly archived for review.
    ids = {t['id'] for t in tasks}
    for tid, prior in old.items():
        if tid not in ids and (prior.get('user_text') or prior.get('completion') == 'done'):
            t = deepcopy(prior)
            t.update(readiness='stale', review_reason='route_removed', completion='todo')
            tasks.append(t)
    return dict(schema_version=2, profile_version=profile_version,
                plan_version=previous.get('plan_version', 0) + 1, as_of=as_of, locale=locale,
                tasks=tasks, enquiries=enquiries, source_versions=versions, notes=previous.get('notes', ''))

def validate_import(raw, catalog):
    portable = PortablePlan.model_validate(raw).model_dump()
    programs = {p['id']: p for p in catalog['programs']}
    sources = {s['id'] for s in catalog['sources']}
    for t in portable['plan']['tasks']:
        p = programs.get(t['program_id'])
        if not p or t['id'] not in {p['id']+'.'+s['id'] for s in p['steps']}:
            raise ValueError('Unknown task')
        step = next(s for s in p['steps'] if t['id'] == p['id']+'.'+s['id'])
        if t['destination'] != step.get('url', p['url']) or t['topic'] != p['topic'] or t['group'] != step['group']:
            raise ValueError('Unknown destination')
        if t['evidence'] != step.get('sources', p['sources']) or set(t['source_versions']) != set(p['sources']):
            raise ValueError('Unknown evidence')
        if t['dependencies'] != p['dependencies'] or set(t['dependency_values']) != set(p['dependencies']):
            raise ValueError('Invalid dependencies')
    if len({t['id'] for t in portable['plan']['tasks']}) != len(portable['plan']['tasks']):
        raise ValueError('Duplicate task')
    for e in portable['plan']['enquiries']:
        if e['program_id'] not in programs:
            raise ValueError('Unknown enquiry')
        p=programs[e['program_id']]
        if e['dependencies'] != p['dependencies'] or set(e['dependency_values']) != set(p['dependencies']) or set(e['source_versions']) != set(p['sources']):
            raise ValueError('Invalid enquiry dependencies')
    if len({e['program_id'] for e in portable['plan']['enquiries']}) != len(portable['plan']['enquiries']):
        raise ValueError('Duplicate enquiry')
    if set(portable['plan']['source_versions']) - sources:
        raise ValueError('Unknown source version')
    return portable
