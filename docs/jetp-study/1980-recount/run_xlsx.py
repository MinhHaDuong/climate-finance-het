import sys; from xl import load; from cmp import *
f=sys.argv[1]; d=load(f)
def rows(t):
    out=[]
    for r in t['rows']:
        v={k.strip():x for k,x in r['vals'].items()}
        if v.get('Beneficiaries') is not None and 'Beneficiary' not in v: v['Beneficiary']=v.pop('Beneficiaries')
        v['_loc']=r['row']; out.append(v)
    return out
o=rows(d['DataTable - Overall'])
regs={s:rows(t) for s,t in d.items() if s!='DataTable - Overall'}
ov,rg,diffs=compare(o,regs,f)
show=sys.argv[2:] 
for fld,lst in diffs.items():
    if show and fld not in show and 'all' not in show: continue
    print('---',fld)
    for x in lst: print('   ',x)
