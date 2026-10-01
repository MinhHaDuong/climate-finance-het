import sys,re,datetime; from xl import load
f=sys.argv[1]; d=load(f)
def rows(t):
    o={}
    for r in t['rows']:
        v={k.strip():x for k,x in r['vals'].items()}
        if 'Beneficiaries' in v: v['Beneficiary']=v.pop('Beneficiaries')
        if v['Unique ID']: o[str(v['Unique ID']).strip()]=v
    return o
ov=rows(d['DataTable - Overall']); rg={}
for s,t in d.items():
    if s!='DataTable - Overall': rg.update(rows(t))
modes={'raw':lambda v:v,'strip':lambda v:v.strip() if isinstance(v,str) else v,
 'ws':lambda v:re.sub(r'\s+',' ',v).strip() if isinstance(v,str) else v,
 'ws+case':lambda v:re.sub(r'\s+',' ',v).strip().lower() if isinstance(v,str) else v}
txt=['Portfolios','Priority Areas','Source','Implementing Entity','Institutional / South African Partner','Beneficiary','Status','Description']
for m,fn in modes.items():
    c={k:sum(1 for i in set(ov)&set(rg) if k in rg[i] and fn(ov[i][k])!=fn(rg[i][k])) for k in txt}
    print(m,c)
# None vs '' and date types
for k in ['Date of Financing Agreement Signed*','End Date']:
    types=set(type(x[k]).__name__ for x in list(ov.values())+list(rg.values()))
    print(k,types, [ (i,x[k]) for i,x in list(ov.items())+list(rg.items()) if isinstance(x[k],str)][:10])
    print('  time-of-day nonzero:',[(i,x[k]) for i,x in ov.items() if isinstance(x[k],datetime.datetime) and x[k].time()!=datetime.time(0)])
# float noise
amt=[(i,ov[i]['Total US$'],rg[i]['Total US$']) for i in set(ov)&set(rg) if ov[i]['Total US$']!=rg[i]['Total US$'] and abs((ov[i]['Total US$'] or 0)-(rg[i]['Total US$'] or 0))<0.5]
print('USD differing only by <0.5:',amt)
amt=[(i,ov[i]['Total ZAR'],rg[i]['Total ZAR']) for i in set(ov)&set(rg) if ov[i]['Total ZAR']!=rg[i]['Total ZAR'] and abs((ov[i]['Total ZAR'] or 0)-(rg[i]['Total ZAR'] or 0))<0.5]
print('ZAR differing only by <0.5:',amt)
