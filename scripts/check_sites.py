import requests
import re
sites=['https://m.cricbuzz.com','https://www.cricbuzz.com','https://www.espncricinfo.com']
for s in sites:
    try:
        r=requests.get(s, timeout=8)
        txt=r.text
        m=re.search(r"(\d{1,3}/\d{1,2}).{0,40}(\d{1,2}\.\d)\s*ov", txt)
        print(s, 'len', len(txt))
        if m:
            print('FOUND', m.group(1), m.group(2))
        else:
            # try simpler: X/Y only
            m2=re.search(r"(\d{1,3}/\d{1,2})", txt)
            print('first XY', m2.group(1) if m2 else 'none')
    except Exception as e:
        print('ERR', s, e)
