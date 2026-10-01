import re, datetime, sys, collections
def ns(v):
    if v is None: return ''
    if isinstance(v,(datetime.datetime,datetime.date)): return v.strftime('%Y-%m-%d')
    if isinstance(v,float) and v.is_integer(): v=int(v)
    return re.sub(r'\s+',' ',str(v)).strip()
def num(v):
    if v is None or v=='': return None
    if isinstance(v,(int,float)): return float(v)
    s=re.sub(r'[\s,$R]','',str(v))
    try: return float(s)
    except: return None
def idnorm(v): return ns(v).upper().replace(' ','')
AMT={'Total US$','Total ZAR'}
def compare(overall, regs, label, tol=0.5):
    """overall: list of dict(field->value, '_loc'); regs: dict id->dict"""
    ov={}; dup=[]
    for r in overall:
        k=idnorm(r['Unique ID'])
        if not k: continue
        if k in ov: dup.append(k)
        ov[k]=r
    rg={}; rdup=[]
    for name,rows in regs.items():
        for r in rows:
            k=idnorm(r['Unique ID'])
            if not k: continue
            if k in rg: rdup.append(k)
            rg[k]=dict(r,_sheet=name)
    print(f'## {label}: overall IDs {len(ov)}, register IDs {len(rg)}; dup overall {dup} dup reg {rdup}')
    print('only overall:',sorted(set(ov)-set(rg)))
    print('only registers:',sorted(set(rg)-set(ov)))
    both=sorted(set(ov)&set(rg))
    print('both:',len(both))
    fields=[f for f in overall[0] if not f.startswith('_') and f!='Unique ID']
    diffs=collections.defaultdict(list)
    for k in both:
        a,b=ov[k],rg[k]
        for f in fields:
            if f not in b: continue
            if f in AMT:
                x,y=num(a[f]),num(b[f])
                if x is None and y is None: continue
                if x is None or y is None or abs(x-y)>tol:
                    diffs[f].append((k,a[f],b[f],(x or 0)-(y or 0)))
            else:
                if ns(a[f])!=ns(b[f]): diffs[f].append((k,ns(a[f])[:70],ns(b[f])[:70],None))
    for f in fields:
        d=diffs.get(f,[])
        extra=''
        if f in AMT and d:
            extra=f' max|d|={max(abs(x[3]) for x in d):,.2f} net={sum(x[3] for x in d):,.2f}'
        print(f'  {f}: {len(d)}{extra}')
    return ov,rg,diffs
