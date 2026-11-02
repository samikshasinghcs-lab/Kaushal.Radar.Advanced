"""AI evaluation: 100 labelled cases for the grounded-brief checker (numbers, entities, direction, superlatives).
31 genuine LLM-drafted briefs + 69 injected hallucinations in 6 types. Seeded. Reports accuracy, misses and failure analysis."""
import re, json, random, csv, collections
src = open('llm_brief_test.py').read().split("assert set(B)")[0]; exec(src)   # loads D (engine rows) and B (31 LLM drafts)
ST, INC = 2.17, 3.86
NAMES = list(D)
ALIAS = {'Ramanagara (Bengaluru South)': ['Ramanagara', 'Bengaluru South'], 'Bengaluru Urban': ['Bengaluru Urban'], 'Bengaluru Rural': ['Bengaluru Rural']}
def names_of(n): return ALIAS.get(n, [n])
SUP = re.compile(r'\b(highest|lowest|largest|smallest|most|least|best|worst|strongest|weakest)\b', re.I)
def checker(text, r):
    why = []
    ok_n = allowed_nums(r)
    for m, dec in nums(text):
        x = float(m.replace(',', '').rstrip('.'))
        if not any(round(a, dec) == x or abs(a - x) < 1e-9 for a in ok_n): why.append('number ' + m)
    # ranks: each ordinal ("4th") must match the engine rank for the basis the sentence names (Census or implied population)
    for sent in re.split(r'(?<=[.;])\s', text):
        parts = re.split(r'\b(\d+)(?:st|nd|rd|th)\b', sent)   # [pre, num, seg, num, seg, ...]
        for i in range(1, len(parts), 2):
            seg = parts[i + 1] if i + 1 < len(parts) else ''
            want = r['rk_dgpi_census'] if re.search(r'census', seg, re.I) else r['rk_dgpi_per_1000']
            if int(parts[i]) != want: why.append('rank ' + parts[i])
    # entities: no other district may be named (own region/neighbour pairs excepted)
    own = names_of(r['name']); okset = set(own) | ({'Vijayanagara'} if r['name'] == 'Ballari' else set()) | ({'Ballari'} if r['name'] == 'Vijayanagara' else set())
    for n in NAMES:
        for a in names_of(n):
            if a not in okset and re.search(r'\b' + re.escape(a) + r'\b', text) and not any(a in o for o in own):
                why.append('other district ' + a)
    if not any(re.search(r'\b' + re.escape(a) + r'\b', text) for a in own): why.append('own district missing')
    # direction vs state average
    for sent in re.split(r'(?<=[.;])\s', text):
        for cl in sent.split(', '):   # clause-level: "below the state average of 2.17, ... income of Rs 6.01 lakh" must not be read as an income claim
            mm = re.search(r'\b(above|below)\b[^.;]*state average', cl, re.I)
            if mm:
                dg_cue = re.search(r'per 1,000|rate|registrants|dgpi|2\.17', cl, re.I)
                use_inc = 'income' in cl.lower() or ('income' in sent.lower() and not dg_cue)
                val, ref = (r['income_lakh'], INC) if use_inc else (r['dgpi_per_1000'], ST)
                if (mm.group(1).lower() == 'above') != (val > ref): why.append('direction ' + mm.group(1))
    status = 'REJECT' if why else 'PASS'
    # superlatives: verified against engine where possible, otherwise sent to a human
    if status == 'PASS':
        for sent in re.split(r'(?<=[.;])\s', text):
            s = SUP.search(sent)
            if not s: continue
            low = sent.lower(); inc = sorted(D.values(), key=lambda x: x['income_lakh'])
            if 'income' in low and ('lowest' in low or 'highest' in low):
                ok = (inc[0]['name'] == r['name']) if 'lowest' in low else (inc[-1]['name'] == r['name'])
                if 'second' in low: ok = inc[-2]['name'] == r['name']
                if 'among' in low: ok = r['income_lakh'] >= inc[-5]['income_lakh']
                if not ok: why.append('false superlative: ' + s.group(1)); status = 'REJECT'
            elif ('registrants' in low or 'count' in low) and re.search(r'largest|smallest', low):
                reg = sorted(D.values(), key=lambda x: x['Grand Total']); ok = (reg[-1]['name'] if 'largest' in low else reg[0]['name']) == r['name']
                if not ok: why.append('false superlative: ' + s.group(1)); status = 'REJECT'
            else:
                why.append('unverifiable superlative: ' + s.group(1)); status = 'REVIEW'
    return status, why
def nums(t): return [(m, len(m.split('.')[1]) if '.' in m else 0) for m in re.findall(r'\d[\d,]*\.?\d*', t)]
def allowed_nums(r):
    base = [r['dgpi_per_1000'], r['rk_dgpi_per_1000'], r['Grand Total'], r['income_lakh'], r['msme_jobs_per_1000'], r['dgpi_census'], r['rk_dgpi_census'], r['p8_imp'], ST, r['dgpi_per_1000'] / ST, 31, 8, 1000, 5000, 100]
    return base + [r['p8_imp'] - 1, r['p8_imp'] + 1] + [r['wpm'], 2011, 2022, 2023, 2025, INC, 9.3, abs(r['rk_dgpi_per_1000'] - r['rk_dgpi_census'])]
rng = random.Random(42)
cases = [(n, 'genuine', t) for n, t in B.items()]
ks = list(B)
def pick(k, pool=None): return rng.sample(pool or ks, k)
for n in pick(20): r = D[n]; f = rng.choice([0.8, 1.25]); v = f"{r['dgpi_per_1000']:.2f}"; cases.append((n, 'wrong_dgpi', B[n].replace(v, f"{r['dgpi_per_1000']*f:.2f}", 1) if v in B[n] else B[n] + f" Its rate is {r['dgpi_per_1000']*f:.2f} per 1,000."))
for n in pick(15):
    rk = D[n]['rk_dgpi_per_1000']; new = rk + rng.choice([-5, -4, -3, 3, 4, 5]); new = min(max(new, 1), 31)
    t = re.sub(r'\b%d(st|nd|rd|th)\b' % rk, f"{new}\\1", B[n], count=1)
    cases.append((n, 'wrong_rank', t if t != B[n] else B[n] + f" It ranks {new}th of 31."))
for n in pick(12):
    other = rng.choice([x for x in ks if x != n and x not in ('Ramanagara (Bengaluru South)', 'Bengaluru Urban', 'Bengaluru Rural')])
    cases.append((n, 'swapped_district', B[n].replace(names_of(n)[0], other, 1)))
for n in pick(10): cases.append((n, 'invented_figure', B[n] + rng.choice([" Its placement rate is 62%.", " About 1,250 graduates found jobs last year.", " Training seats rose 18% in 2025."])))
for n in pick(7, [k for k in ks if k not in ('Dakshina Kannada','Bengaluru Urban','Kalaburagi','Udupi')]): cases.append((n, 'false_superlative', B[n] + " It has the highest per capita income in the state."))
for n in pick(5, [k for k in ks if D[k]['dgpi_per_1000'] < ST]): cases.append((n, 'wrong_direction', B[n] + " Its rate is above the state average."))
assert len(cases) == 100, len(cases)
res = [(n, kind, t) + checker(t, D[n]) for n, kind, t in cases]
gen = [x for x in res if x[1] == 'genuine']
print('GENUINE LLM drafts (31): auto-pass %d, sent to human review %d, false rejects %d' % tuple(sum(1 for x in gen if x[3] == s) for s in ('PASS', 'REVIEW', 'REJECT')))
for x in gen:
    if x[3] != 'PASS': print('   ', x[3], x[0], x[4])
print('INJECTED hallucinations (69): caught = REJECT or REVIEW; missed = PASS')
tot = collections.Counter(); caught = collections.Counter()
for n, kind, t, st, why in res:
    if kind == 'genuine': continue
    tot[kind] += 1; caught[kind] += st != 'PASS'
for k in tot: print('   %-18s caught %2d / %2d' % (k, caught[k], tot[k]))
print('   TOTAL caught %d / 69 (%.0f%%)' % (sum(caught.values()), 100 * sum(caught.values()) / 69))
acc = (sum(1 for x in gen if x[3] != 'REJECT') + sum(caught.values())) / 100
print('Overall case-level accuracy (genuine not rejected + hallucination caught): %.0f%%' % (100 * acc))
for n, kind, t, st, why in res:
    if kind != 'genuine' and st == 'PASS': print('MISS', kind, n, '|', t[:120])
with open('ai_eval_cases.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f); w.writerow(['district', 'case_type', 'text', 'checker_status', 'reasons']); [w.writerow([n, k, t, s, '; '.join(w_)]) for n, k, t, s, w_ in res]

print('--- engine values behind the 3 genuine rejects:')
for n in ('Shivamogga','Belagavi','Udupi'):
    r=D[n]; print('   ',n,'p8_imp now',r['p8_imp'],'| dgpi',round(r['dgpi_per_1000'],2),'| income',round(r['income_lakh'],2))
