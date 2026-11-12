// Offline keyword reader vs Claude on the same ten goals (no network, no key).
// Uses the recorded Claude answers in reports/ai_quality_evaluation.json and VERA's real browser code.
// Run: node scripts/compare_offline_ai.mjs   ->  reports/offline_vs_ai.json
import fs from 'node:fs';
import {detectTopics, proposeFacts} from '../web/navigator.js';
import {screen, screenedPrograms} from '../web/screening.js';

const read = p => JSON.parse(fs.readFileSync(new URL(`../${p}`, import.meta.url), 'utf8'));
const cases = read('data/fixtures/ai_quality_cases.json').cases;
const ai = Object.fromEntries(read('reports/ai_quality_evaluation.json').results.map(r => [r.id, r]));
const rules = read('dist/catalog.json');
const asOf = rules.compiled_on;
const confirmed = facts => Object.fromEntries(Object.entries(facts).map(([k, v]) =>
  [k, {value: v, state: ['unknown', 'declined'].includes(v) ? v : 'confirmed', version: 1, confirmed_at: null}]));
const profile = (goals, facts) => ({goals, priority: goals[0] || null, facts: confirmed(facts)});
const states = r => Object.fromEntries(Object.entries(r.draft).map(([k, v]) => [k, v.state]));

function score(prefilled, expected) {
  const right = Object.keys(expected).filter(k => prefilled[k] === expected[k]);
  const wrong = Object.keys(prefilled).filter(k => k in expected ? prefilled[k] !== expected[k] : !['unknown', 'declined'].includes(prefilled[k]));
  const byHand = Object.keys(expected).filter(k => prefilled[k] !== expected[k]);  // typed or fixed by the person
  return {right, wrong, byHand};
}

const rows = [];
for (const c of cases) {
  const r = ai[c.id];
  const off = {topics: detectTopics(c.message), facts: proposeFacts(c.message)};
  const on = {topics: r.topics, facts: r.proposed_facts};
  const so = score(off.facts, c.expected), sa = score(on.facts, c.expected);
  // Right after the first sentence, before any typing: which screened programs already have a result?
  const decided = (p) => Object.values(states(screen(p, rules, {asOf}))).filter(s => s !== 'needs_information').length;
  const offProfile = profile(off.topics, Object.fromEntries(so.right.map(k => [k, c.expected[k]]).concat(so.wrong.filter(k => k in c.expected === false).map(k => [k, off.facts[k]]))));
  const offStart = profile(off.topics, off.facts), onStart = profile(on.topics, on.facts);
  // Same final answers both ways: the person ends with the facts they stated, on the same topics.
  const goals = on.topics;
  const same = JSON.stringify(states(screen(profile(goals, c.expected), rules, {asOf}))) ===
               JSON.stringify(states(screen(profile(goals, on.facts), rules, {asOf})));
  rows.push({id: c.id, locale: c.locale, style: c.style, stated_facts: Object.keys(c.expected).length,
    offline: {topics: off.topics, proposed: off.facts, right: so.right.length, wrong: so.wrong, by_hand: so.byHand.length,
              screened_programs: screenedPrograms(offStart).length, results_after_first_sentence: decided(offStart)},
    ai: {topics: on.topics, proposed: on.facts, right: sa.right.length, wrong: sa.wrong, by_hand: sa.byHand.length,
         screened_programs: screenedPrograms(onStart).length, results_after_first_sentence: decided(onStart)},
    same_screening_result_after_confirming: same});
}
const sum = (side, k) => rows.reduce((n, r) => n + (Array.isArray(r[side][k]) ? r[side][k].length : r[side][k]), 0);
const summary = {
  cases: rows.length, stated_facts: rows.reduce((n, r) => n + r.stated_facts, 0),
  offline: {facts_right: sum('offline', 'right'), facts_wrong: sum('offline', 'wrong'), facts_by_hand: sum('offline', 'by_hand'),
            no_topic_found: rows.filter(r => !r.offline.topics.length).length,
            programs_with_result_after_first_sentence: sum('offline', 'results_after_first_sentence'), programs_screened: sum('offline', 'screened_programs')},
  ai: {facts_right: sum('ai', 'right'), facts_wrong: sum('ai', 'wrong'), facts_by_hand: sum('ai', 'by_hand'),
       no_topic_found: rows.filter(r => !r.ai.topics.length).length,
       programs_with_result_after_first_sentence: sum('ai', 'results_after_first_sentence'), programs_screened: sum('ai', 'screened_programs')},
  same_screening_result: `${rows.filter(r => r.same_screening_result_after_confirming).length}/${rows.length}`,
  note: 'Draft rule logic. "Result" = any state other than needs_information. Same final facts give the same result because the written rules decide, not the AI.',
};
fs.writeFileSync(new URL('../reports/offline_vs_ai.json', import.meta.url), JSON.stringify({summary, rows}, null, 2) + '\n');
console.log(JSON.stringify(summary, null, 1));
for (const r of rows) console.log(r.id, '| offline', r.offline.right + '/' + r.stated_facts, 'wrong', r.offline.wrong.join(',') || '-', 'topics', r.offline.topics.join(',') || 'NONE',
  'results', r.offline.results_after_first_sentence + '/' + r.offline.screened_programs, '| ai', r.ai.right + '/' + r.stated_facts, 'topics', r.ai.topics.join(','), 'results', r.ai.results_after_first_sentence + '/' + r.ai.screened_programs, '| same', r.same_screening_result_after_confirming);
