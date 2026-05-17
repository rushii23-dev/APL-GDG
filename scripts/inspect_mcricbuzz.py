from bs4 import BeautifulSoup
import requests
url='https://m.cricbuzz.com/cricket-match/live-scores'
r=requests.get(url, timeout=10)
soup=BeautifulSoup(r.text,'html.parser')
count=0
for a in soup.select('a'):
    href=a.get('href')
    if href and '/cricket-match' in href:
        txt=a.get_text(separator=' ').strip()
        if 'IPL' in txt or 'Indian' in txt or 'Indian Premier' in txt:
            print('HREF',href)
            print('TXT',txt[:200])
            count+=1
            if count>6: break
print('count',count)
