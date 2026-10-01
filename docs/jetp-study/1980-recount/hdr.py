import pdfplumber
def header(p):
    ws=p.extract_words()
    u=[w for w in ws if w['text']=='Unique']
    if not u: return None,None
    top=u[0]['top']
    h=sorted([w for w in ws if abs(w['top']-top)<3],key=lambda w:w['x0'])
    cl=[]
    for w in h:
        if cl and w['x0']-cl[-1]['x1']<7: cl[-1]['x1']=w['x1']; cl[-1]['t']+=' '+w['text']
        else: cl.append(dict(x0=w['x0'],x1=w['x1'],t=w['text']))
    return top,cl
if __name__=='__main__':
    pdf=pdfplumber.open('q2.pdf')
    for i,p in enumerate(pdf.pages):
        top,cl=header(p)
        print(i+1,round(top or 0),[(c['t'],round(c['x0'])) for c in cl or []])
