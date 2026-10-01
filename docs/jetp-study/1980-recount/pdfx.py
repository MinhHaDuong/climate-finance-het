import pdfplumber, re, json, sys
from hdr import header
CANON={'Unique ID':'Unique ID','Portfolios':'Portfolios','Priority Areas':'Priority Areas','Total US$':'Total US$','Total ZAR':'Total ZAR',
 'Source':'Source','Implementing Entity':'Implementing Entity','Status':'Status','Description':'Description','Beneficiaries':'Beneficiary',
 'Implementing Partners':'Implementing Partners','End Date':'End Date'}
def cols(cl):
    out=[]
    for c in cl:
        t=c['t']
        if t.startswith('Date of Financing'):
            out.append(('Signed',c['x0']))
            if 'End Date' in t or 'End' not in t: pass
        elif t=='CHF: Amount Total ZAR':
            out.append(('Home',c['x0'])); out.append(('Total ZAR',None))
        elif 'Amount' in t: out.append(('Home',c['x0']))
        else: out.append((CANON.get(t,t),c['x0']))
    return out
ID=re.compile(r'^(EU|UK|GR|FR|US|ACTIP|DK|NL|CAN|SW)\d{3}[A-Za-z*]*$')
DATE=re.compile(r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s*(\d{1,2})\s+([A-Z][a-z]+)\s+(\d{4})')
MON={m:i+1 for i,m in enumerate('January February March April May June July August September October November December'.split())}
def run(path):
    pdf=pdfplumber.open(path)
    tables=[]; cur=None; log=[]
    for pi,p in enumerate(pdf.pages):
        txt=(p.extract_text() or '')
        title=re.search(r'^(DATATABLE OVERALL|[A-Z]+-REGISTER)',txt,re.M)
        top,cl=header(p)
        if title:
            cur=dict(title=title.group(1),rows=[],pages=[]); tables.append(cur)
        cur['pages'].append(pi+1)
        cs=cols(cl)
        # resolve CHF merged: find 'Total' word x within merged cluster
        ws=p.extract_words()
        hw=[w for w in ws if abs(w['top']-top)<3]
        for i,(n,x) in enumerate(cs):
            if n=='Total ZAR' and x is None:
                x=[w['x0'] for w in hw if w['text']=='Total' and w['x0']>cs[i-1][1]][0]; cs[i]=(n,x)
        signed_x=[x for n,x in cs if n=='Signed'][0]
        wide=[r for r in p.rects if r['width']>300]
        right=max(r['x1'] for r in wide)
        has_end=any(n=='End Date' for n,x in cs)
        endthr=[x for n,x in cs if n=='End Date'][0]-3 if has_end else None
        bounds=sorted(set([round(r['top'],1) for r in wide]+[round(r['bottom'],1) for r in wide]))
        hb=min(b for b in bounds if b>top+2)  # header bottom
        bl=[b for b in bounds if b>=hb]
        # merge near-duplicates
        m=[]
        for b in bl:
            if not m or b-m[-1]>2: m.append(b)
        edges=[x for n,x in cs]
        names=[n for n,x in cs]
        # date column: treat signed..right as single date zone
        for a,b in zip(m,m[1:]):
            band=[w for w in ws if a<=(w['top']+w['bottom'])/2<b]
            if not band: continue
            cells={n:[] for n in names}
            datez=[]
            for w in band:
                if w['x0']>=signed_x-3: datez.append(w); continue
                idx=max(i for i,e in enumerate(edges) if w['x0']>=e-4) if w['x0']>=edges[0]-4 else 0
                cells[names[idx]].append(w)
            row={n:' '.join(w['text'] for w in sorted(v,key=lambda w:(round(w['top']),w['x0']))) for n,v in cells.items()}
            dz=sorted(datez,key=lambda w:(round(w['top']),w['x0']))
            dtxt=' '.join(w['text'] for w in dz)
            dates=[]
            for mm in DATE.finditer(dtxt):
                # x of weekday word
                wd=[w for w in dz if w['text'].startswith(mm.group(1))]
                dates.append((mm,))
            # assign by x of weekday tokens
            wds=[w for w in dz if re.match(r'(Mon|Tues|Wednes|Thurs|Fri|Satur|Sun)day,',w['text'])]
            parsed=[f'{int(x.group(4)):04d}-{MON[x.group(3)]:02d}-{int(x.group(2)):02d}' for x in DATE.finditer(dtxt)]
            thr=endthr if endthr else (signed_x+right)/2
            row['Signed']='';row['End Date']=''
            if len(parsed)==len(wds):
                for w,d in zip(sorted(wds,key=lambda w:(round(w['top']),w['x0'])),parsed):
                    row['End Date' if w['x0']>=thr else 'Signed']=d
            else: log.append(('date-parse',pi+1,row.get('Unique ID'),dtxt))
            row['_dates_raw']=dtxt
            row['_page']=pi+1; row['_band']=(a,b)
            uid=row['Unique ID'].strip()
            if ID.match(uid) or uid:
                cur['rows'].append(row)
            else:
                cur['rows'].append(dict(row,_noid=True))
    return tables,log
if __name__=='__main__':
    t,log=run(sys.argv[1])
    json.dump(dict(tables=t,log=log),open('q2_extract.json','w'),indent=1,default=str)
    for tb in t:
        ids=[r['Unique ID'] for r in tb['rows']]
        print(tb['title'],tb['pages'],len(ids),'noid',sum(1 for r in tb['rows'] if r.get('_noid')))
        print('   ',ids)
    print(log)
