// Hybrid screening: the original Mei / Tomás journeys inside the v2 navigator. No network, no model.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {screen, nextQuestion, diffResults, withAnswer, screenedPrograms, engineFacts} from '../web/screening.js';
import {Workspace, validatePortable, validateProfile} from '../web/navigator.js';
import {facts as checkProposals} from '../worker/contracts.js';

const rules = JSON.parse(fs.readFileSync(new URL('../dist/catalog.json', import.meta.url)));
const catalog = JSON.parse(fs.readFileSync(new URL('../data/catalog/navigation.json', import.meta.url)));
const asOf = rules.compiled_on;
const fact = v => ({value: v, state: ['unknown', 'declined'].includes(v) ? v : 'confirmed', version: 1, confirmed_at: null});
const profile = (goals, facts = {}) => ({goals, priority: goals[0] || null,
  facts: Object.fromEntries(Object.entries(facts).map(([k, v]) => [k, fact(v)]))});
const states = (r, kind = 'draft') => Object.fromEntries(Object.entries(r[kind]).map(([k, v]) => [k, v.state]));

test('Topics choose the screened programs; other topics stay preparation-only', () => {
  assert.deepEqual(screenedPrograms(profile(['settlement', 'education'])), ['STU-01', 'NEW-02', 'NEW-03']);
  assert.deepEqual(screenedPrograms(profile(['education'])), ['STU-01']);
  assert.deepEqual(screenedPrograms(profile(['banking', 'taxes', 'benefits'])), []);
});

test('Mei: questions arrive one at a time in a fixed order', () => {
  let p = profile(['settlement', 'education'], {province: 'BC', institution: 'sfu'});
  const asked = [];
  for (const [key, value] of [['status', 'study_permit'], ['student', 'yes'], ['institution_service', 'no'], ['special_pathway', 'no']]) {
    const q = nextQuestion(p, screen(p, rules, {asOf}));
    asked.push(q);
    p = withAnswer(p, key, value);
  }
  assert.deepEqual(asked, ['status', 'student', 'institution_service', 'special_pathway']);
  assert.equal(nextQuestion(p, screen(p, rules, {asOf})), null);
});

test('Mei: draft logic matches the persona expectations', () => {
  const p = profile(['settlement', 'education'], {status: 'study_permit', student: 'yes'});
  assert.deepEqual(states(screen(p, rules, {asOf})),
    {'STU-01': 'blocker_found', 'NEW-02': 'needs_information', 'NEW-03': 'needs_information'});
});

test('Mei correction changes only BC NSP', () => {
  const p = profile(['settlement', 'education'], {status: 'study_permit', student: 'yes', special_pathway: 'no'});
  const before = screen(p, rules, {asOf});
  const after = screen(withAnswer(p, 'institution_service', 'no'), rules, {asOf});
  const changes = diffResults(before, after, 'institution_service');
  assert.deepEqual(changes.map(c => c.program_id), ['NEW-02']);
  assert.equal(changes[0].draft_after, 'no_blocker_in_checked_criteria');
});

test('Unreviewed rules are shown as needs official review, never as a decision', () => {
  const p = profile(['settlement', 'education'], {status: 'study_permit', student: 'yes', institution_service: 'no'});
  const r = screen(p, rules, {asOf});
  assert(Object.values(states(r, 'displayed')).every(s => s === 'needs_official_review'));
  assert(Object.values(r.displayed).every(x => x.rules.every(rule => rule.gated)));
});

test('Proposed (unconfirmed) facts never reach the rules engine', () => {
  const p = profile(['settlement'], {});
  p.facts.status = {value: 'study_permit', state: 'proposed', version: 0, confirmed_at: null};
  assert.equal(engineFacts(p).status_category, null);
  assert.equal(nextQuestion(p, screen(p, rules, {asOf})), 'status');
});

test('A skipped question is not asked again', () => {
  const p = withAnswer(profile(['settlement'], {status: 'study_permit', student: 'yes'}), 'institution_service', 'unknown');
  const q = nextQuestion(p, screen(p, rules, {asOf}), new Set(['institution_service']));
  assert.notEqual(q, 'institution_service');
});

test('Tomás: economic PR with a month goes to official review, no date calculation', () => {
  const p = profile(['settlement'], {status: 'permanent_resident', pr_class: 'economic', pr_month: '2021-06'});
  assert.equal(screen(p, rules, {asOf}).draft['NEW-03'].state, 'needs_official_review');
});

test('Answers are validated; month must be YYYY-MM', () => {
  const p = profile(['settlement']);
  assert.throws(() => withAnswer(p, 'status', 'passport'));
  assert.throws(() => withAnswer(p, 'pr_month', '2021-13'));
  assert.throws(() => withAnswer(p, 'sin', '123'));
  assert.equal(withAnswer(p, 'pr_month', '2021-06').facts.pr_month.value, '2021-06');
  assert.throws(() => validateProfile(profile(['settlement'], {pr_month: 'June'})));
});

test('Screening answers survive the v2 plan, export and import', () => {
  const w = new Workspace(catalog);
  w.confirm(profile(['settlement', 'education', 'banking'], {province: 'BC', institution: 'sfu', status: 'study_permit', student: 'yes', special_pathway: 'no'}));
  assert(w.plan.tasks.some(t => t.topic === 'banking'));
  const raw = w.portable();
  const back = validatePortable(raw, catalog);
  assert.equal(back.profile.facts.special_pathway.value, 'no');
});

test('The OpenAI intake may propose screening facts, but only listed values', () => {
  assert.doesNotThrow(() => checkProposals([{field: 'special_pathway', value: 'no'}, {field: 'pr_month', value: '2021-06'}]));
  assert.throws(() => checkProposals([{field: 'special_pathway', value: 'eligible'}]));
  assert.throws(() => checkProposals([{field: 'eligibility', value: 'yes'}]));
});
