import json,re,csv
d=json.load(open('lists_raw.json'))
FIX={'wael':{9:'Falafel Hassoun',28:'Phở Hưng Restaurant',33:'Yakiniku Legend',35:'Earls Kitchen + Bar',39:'LOCAL Public Eatery Adelaide',40:'Cheng Du Street Food',43:"Nina's Brunch Restaurant",51:'Love And Meat Restaurant Rixos Premium Belek',54:'The Keg Steakhouse + Bar - Signal Hill',60:'Good Behaviour Ice Cream and Sub Sandwiches',67:"Benny's Barbecue",85:'Monkey Sushi - Edward',109:'Magical Taste of China Downtown',110:'Zafoon Middle Eastern Restaurant',111:'Notte Ristorante (formerly Amano Trattoria)',125:'Seoul Gamjatang Korean Restaurant',126:'Al Baik',133:'Añejo Restaurant',134:'The View Lounge - Gates B',136:'OPA! of Greece Chinook Mall',143:"Hemingway's Restaurant and Bar",148:'Petit Potato',152:'Scotiabank Arena',156:'Bestco Fresh Foods Downtown Store',160:"Osmow's Shawarma",163:'Mogouyan Hand-Pulled Noodles',164:'A&W Canada',181:"Nature's Emporium",185:"Burgers n' Fries Forever"},
 'zed':{1:'Pizzéria NO.900 - Peel',5:'Le Flamant Rose Restaurant & Cafe',17:'Sumaq Iraqi Charcoal Grill - Mississauga',22:"L'avenue",53:'Al Mashawi Al Halabya - Al Barsha',67:'Sumaq Iraqi Charcoal Grill - Queen St West',77:'Abu Shakra Restaurant & Cafe',80:'Cheng Du Street Food',94:'Añejo Restaurant',96:'Good Behaviour Ice Cream and Sub Sandwiches',110:"Hemingway's Restaurant and Bar",127:'Pickl',129:"L'Antica Pizzeria da Michele",158:'The Queen & Beaver Public House',161:'Izmir Saray Turkish Restaurant Seashell',164:"Benny's Barbecue",181:'Blondies Pizza',185:'Kata Sushi'}}
LOCFIX={('wael',51):'Belek, Turkey',('wael',118):'Tekirova, Turkey',('wael',134):'Airport lounge',('zed',174):'Sugar Creek, MO, USA'}
DROP={'wael':{1},'zed':{8,186}}
GTA=re.compile(r'Toronto|Mississauga|Vaughan|Oakville|Brampton|Markham|Thornhill',re.I)
out={}
for who,rows in d.items():
    res=[]
    for r in rows:
        if r['rank'] in DROP[who]: continue
        n=r['name']; sc=r['score']
        n=re.sub(r'\s*(\(\w*\)|\(\s*\))?\s*(Q[tU]?\)?|\(?WU\)?|\(0\)|0|1\))?\s*V(iew)?\s*M(ap?)?.*$','',n)
        m=re.search(r'\s(\d)(\d)(\s|$)',n)
        if m and sc is None: sc=f'{m.group(1)}.{m.group(2)}'; n=(n[:m.start()]+' '+n[m.end():]).strip()
        n=FIX[who].get(r['rank'],n).strip(' .|_')
        res.append(dict(rank=r['rank'],name=n,score=float(sc.replace(',','.')) if sc else None,location=LOCFIX.get((who,r['rank']),r['loc'] or '')))
    # repair scores: must be non-increasing; '3' misread for '8'
    for i,x in enumerate(res):
        prev=next((y['score'] for y in reversed(res[:i]) if y['score'] is not None),10.0)
        if x['score'] is not None and x['score']<prev-1.5 and x['score']+5<=prev+0.01: x['score']=round(x['score']+5,1)
    for i,x in enumerate(res):
        if x['score'] is None:
            a=next((y['score'] for y in reversed(res[:i]) if y['score'] is not None),None); b=next((y['score'] for y in res[i+1:] if y['score'] is not None),None)
            x['score']=a if a==b else None
    for x in res: x['gta']=bool(GTA.search(x['location']))
    bad=[(res[i]['rank'],res[i]['score']) for i in range(1,len(res)) if res[i]['score'] and res[i-1]['score'] and res[i]['score']>res[i-1]['score']]
    print(who,len(res),'GTA',sum(x['gta'] for x in res),'order violations',bad,'missing score',[x['rank'] for x in res if x['score'] is None])
    out[who]=res
    with open(f'ranking_{who}_final.csv','w',newline='') as f:
        w=csv.writer(f); w.writerow(['rank','name','score','location','toronto_area'])
        for x in res: w.writerow([x['rank'],x['name'],x['score'] if x['score'] is not None else '',x['location'],x['gta']])
json.dump(out,open('lists_final.json','w'),ensure_ascii=False)
for who in out:
    print('---',who); print('; '.join(f"{x['rank']} {x['name']}" for x in out[who] if re.search(r'[^\x00-\x7FéêèÉàçñöüőởư]|  |\d{2}$',x['name'])))
