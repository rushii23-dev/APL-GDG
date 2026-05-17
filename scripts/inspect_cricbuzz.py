from bs4 import BeautifulSoup
import requests
url='https://www.cricbuzz.com/cricket-match/live-scores'
r=requests.get(url, timeout=10)
soup=BeautifulSoup(r.text,'html.parser')
# print anchors with /cricket-match
count=0
for a in soup.select('a'):
    href=a.get('href')
    if href and '/cricket-match' in href:
        txt=a.get_text(separator=' ').strip()
        print('HREF:',href)
        print('TXT:', txt[:200])
        print('-'*40)
        count+=1
        if count>=8:
            break

print('\n--- SEARCH FOR SCORE-SPECIFIC CLASSES ---\n')
for cls in ['cb-scrs-wrp','cb-scrs','match-score','cb-col']:
    found = bool(soup.find(class_=cls))
    print(cls, 'present?', found)
