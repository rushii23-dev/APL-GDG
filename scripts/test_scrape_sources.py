import requests
from bs4 import BeautifulSoup

urls = [
    'https://m.cricbuzz.com/cricket-match/live-scores',
    'https://www.cricbuzz.com/cricket-match/live-scores',
    'https://www.espncricinfo.com/ci/engine/match/index.html?view=live',
]

for u in urls:
    print('\n---', u)
    try:
        r = requests.get(u, timeout=10, headers={'User-Agent':'Mozilla/5.0'})
        print('status', r.status_code)
        txt = r.text[:8000]
        print('snippet:\n', txt[:2000])
        soup = BeautifulSoup(r.text, 'html.parser')
        # look for score patterns
        body = soup.get_text(separator=' ', strip=True)
        import re
        m = re.search(r"(\d{1,3}/\d{1,2})\s*\(?\s*(\d{1,2}\.\d)\s*(ov|overs)?", body)
        if m:
            print('found pattern:', m.groups())
        else:
            print('no direct pattern in text')
        # anchors
        anchors = [a.get('href') for a in soup.find_all('a', href=True) if 'match' in a.get('href') or 'live' in a.get('href')]
        print('sample anchors count', len(anchors))
        for a in anchors[:10]:
            print('  ', a)
    except Exception as e:
        print('error', e)
