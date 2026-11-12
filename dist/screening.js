// Hybrid screening: the original three-program journey (STU-01, NEW-02, NEW-03) inside the v2 navigator.
// Eligibility logic is NOT written here. It is compiled from rules.py into catalog.json and run by engine.js.
// This module only maps confirmed profile facts to engine inputs, picks the next question, and diffs results.
import {checkProgram} from './engine.js';

export const SCREEN_PROGRAMS = ['STU-01', 'NEW-02', 'NEW-03'];

// engine field -> profile fact key
export const ENGINE_TO_PROFILE = {
  status_category: 'status',
  is_post_secondary_student: 'student',
  institution_offers_service: 'institution_service',
  bc_resident: 'province',
  naturalized_citizen: 'naturalized',
  federal_exception: 'special_pathway',
  pr_class: 'pr_class',
  pr_landing_date: 'pr_month',
};

// Fields the screening may ask, with the answer options shown (profile values).
export const SCREEN_QUESTIONS = {
  status: ['study_permit', 'work_permit', 'permanent_resident', 'protected_person', 'citizen', 'other', 'declined', 'unknown'],
  student: ['yes', 'no', 'unknown'],
  institution_service: ['yes', 'no', 'unknown'],
  naturalized: ['yes', 'no', 'unknown'],
  special_pathway: ['yes', 'no', 'unknown'],
  pr_class: ['economic', 'family', 'refugee', 'other', 'unknown'],
  pr_month: null, // month picker, YYYY-MM
};

const confirmed = (profile, key) => {
  const f = profile.facts?.[key];
  return f && f.state === 'confirmed' ? f.value : (f?.state === 'declined' ? 'declined' : 'unknown');
};

const tri = v => (v === 'yes' || v === 'no' ? v : 'unknown');

/** Programs to screen, from the person's chosen topics. Other topics stay preparation-only. */
export function screenedPrograms(profile) {
  const goals = profile.goals || [];
  const ids = [];
  if (goals.includes('education')) ids.push('STU-01');
  if (goals.includes('settlement')) ids.push('NEW-02', 'NEW-03');
  return SCREEN_PROGRAMS.filter(id => ids.includes(id));
}

/** Map confirmed profile facts to the engine's input facts. Proposed (unconfirmed) facts are ignored. */
export function engineFacts(profile) {
  const status = confirmed(profile, 'status');
  const province = confirmed(profile, 'province');
  const prClass = confirmed(profile, 'pr_class');
  const prMonth = confirmed(profile, 'pr_month');
  return {
    status_category: status === 'unknown' ? null : status === 'declined' ? 'prefer_not_to_say' : status,
    is_post_secondary_student: tri(confirmed(profile, 'student')),
    institution_offers_service: tri(confirmed(profile, 'institution_service')),
    bc_resident: province === 'BC' ? 'yes' : province === 'other' ? 'no' : 'unknown',
    naturalized_citizen: tri(confirmed(profile, 'naturalized')),
    federal_exception: tri(confirmed(profile, 'special_pathway')),
    pr_class: ['economic', 'family', 'refugee', 'other'].includes(prClass) ? prClass : null,
    pr_landing_date: /^\d{4}-\d{2}$/.test(prMonth) ? prMonth + '-01' : null,
  };
}

/**
 * Run the compiled rules for every screened program.
 * Returns {displayed, draft}: displayed applies the approval gate (live behaviour);
 * draft shows what the unreviewed rule logic would say (labelled demo only).
 */
export function screen(profile, rulesCatalog, {asOf, version = 1} = {}) {
  const facts = engineFacts(profile);
  const out = {displayed: {}, draft: {}};
  for (const pid of screenedPrograms(profile)) {
    out.displayed[pid] = checkProgram(pid, facts, rulesCatalog, false, version, asOf);
    out.draft[pid] = checkProgram(pid, facts, rulesCatalog, true, version, asOf);
  }
  return out;
}

/**
 * Next question to ask, or null. Status comes first; then any input a draft rule reports missing.
 * Uses draft logic to find missing inputs so the journey works before rules are approved,
 * but never shows a draft result as a decision. Skipped fields are not asked again.
 */
export function nextQuestion(profile, results, skipped = new Set()) {
  if (!screenedPrograms(profile).length) return null;
  const engineMissing = Object.values(results.draft).flatMap(r => r.missing);
  const order = ['status', ...engineMissing.map(f => ENGINE_TO_PROFILE[f]).filter(Boolean)];
  for (const key of order) {
    if (!(key in SCREEN_QUESTIONS) || skipped.has(key)) continue;
    const v = confirmed(profile, key);
    if (v === 'unknown') return key;
  }
  return null;
}

/** Programs whose state changed between two screenings, for the "what changed" panel. */
export function diffResults(before, after, field) {
  const changes = [];
  for (const pid of Object.keys(after.draft)) {
    const b = before?.draft?.[pid], a = after.draft[pid];
    const bd = before?.displayed?.[pid], ad = after.displayed[pid];
    const draftChanged = !b || b.state !== a.state || JSON.stringify(b.rules.map(r => r.outcome)) !== JSON.stringify(a.rules.map(r => r.outcome));
    const shownChanged = !bd || bd.state !== ad.state;
    if (draftChanged || shownChanged) {
      changes.push({program_id: pid, field, shown_before: bd?.state ?? null, shown_after: ad.state,
        draft_before: b?.state ?? null, draft_after: a.state});
    }
  }
  return changes;
}

/** Return a copy of the profile with one screening answer recorded as confirmed (or unknown/declined). */
export function withAnswer(profile, key, value) {
  if (!(key in SCREEN_QUESTIONS)) throw Error('unknown_question');
  const allowed = SCREEN_QUESTIONS[key];
  if (allowed ? !allowed.includes(value) : !(value === 'unknown' || /^\d{4}-(0[1-9]|1[0-2])$/.test(value))) throw Error('invalid_answer');
  const next = JSON.parse(JSON.stringify(profile));
  const old = next.facts[key];
  next.facts[key] = {value, state: ['unknown', 'declined'].includes(value) ? value : 'confirmed',
    version: old?.version || 0, confirmed_at: old?.confirmed_at || null};
  return next;
}
