import json,re,collections,sys
d=json.load(open('q2_extract.json'))
def amt(s):
    if not s: return None
    if '#' in s: return '###'
    t=re.sub(r'(kr\.|CHF|[$£€R\s,])','',s)
    try: return float(t)
    except: return 'BAD:'+s
def tnorm(s,mode):
    s=s or ''
    if mode=='ws': return re.sub(r'\s+',' ',s).strip()
    if mode=='loose': return re.sub(r'[\s\-]','',s).lower()
ov={};rg={};dups=[]
for t in d['tables']:
    for r in t['rows']:
        if r.get('_noid'): continue
        k=r['Unique ID'].strip()
        tgt=ov if t['title']=='DATATABLE OVERALL' else rg
        if k in tgt: dups.append((t['title'],k))
        tgt[k]=dict(r,_t=t['title'])
print('dups',dups)
print('overall',len(ov),'registers',len(rg))
print('only overall',sorted(set(ov)-set(rg)), len(set(ov)-set(rg)))
print('only registers',sorted(set(rg)-set(ov)))
both=sorted(set(ov)&set(rg)); print('both',len(both))
# amount parse problems
for src,D in (('ov',ov),('rg',rg)):
    for k,r in D.items():
        for f in ('Total US$','Total ZAR','Home'):
            if f in r and not isinstance(amt(r[f]),float): print('AMT?',src,k,f,repr(r[f]))
for mode in ('ws','loose'):
    print('== text mode',mode)
    for f in ['Portfolios','Priority Areas','Source','Implementing Entity','Status','Description']:
        dl=[(k,tnorm(ov[k][f],mode)[:60],tnorm(rg[k][f],mode)[:60]) for k in both if tnorm(ov[k][f],mode)!=tnorm(rg[k][f],mode)]
        print(f,len(dl))
        if mode=='loose' or f!='Description':
            for x in dl[:25]: print('    ',x)
for f in ['Signed','End Date']:
    dl=[(k,ov[k][f],rg[k][f]) for k in both if ov[k][f]!=rg[k][f]]
    print(f,len(dl),dl)
for f in ['Total US$','Total ZAR']:
    dl=[]
    for k in both:
        a,b=amt(ov[k][f]),amt(rg[k][f])
        if not(isinstance(a,float) and isinstance(b,float)):
            if a!=b: dl.append((k,ov[k][f],rg[k][f],None))
            continue
        if abs(a-b)>1: dl.append((k,a,b,a-b))
    nums=[x[3] for x in dl if x[3] is not None]
    print(f,len(dl),'max',max(map(abs,nums)) if nums else 0,'net',sum(nums))
    for x in dl: print('    ',x)
