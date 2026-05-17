import requests
from bs4 import BeautifulSoup
u = 'https://www.cricbuzz.com/live-cricket-score/53039/rcb-vs-pbks-61st-match-indian-premier-league-2026'
# Note: the actual link pattern may differ; try a known anchor from previous run
# We'll try constructing from anchor found earlier
u = 'https://www.cricbuzz.com/live-cricket-scores/152174/rcb-vs-pbks-61st-match-indian-premier-league-2026'
print('fetching', u)
r = requests.get(u, timeout=10, headers={'User-Agent':'Mozilla/5.0'})
print('status', r.status_code)
print(r.text[:4000])

soup = BeautifulSoup(r.text, 'html.parser')
# find scorecard style spans or divs
for cls in ['cb-scrs-wrp','cb-col cb-col-100 cb-scrs','cb-min-rw']:
    el = soup.find(class_=cls)
    if el:
        print('found element for', cls)
        print(el.get_text('\n')[:600])
# generic search for patterns
print('\n---- text search ----')
text = soup.get_text(separator=' ', strip=True)
import re
m = re.search(r"(\d{1,3}/\d{1,2})\s*\(?\s*(\d{1,2}\.\d)\s*(ov|overs)?", text)
print('pattern', bool(m))
if m: print(m.groups())
print('\n--- done')
