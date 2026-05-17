from bs4 import BeautifulSoup
import requests
r = requests.get('https://www.cricbuzz.com/cricket-match/live-scores', timeout=10)
soup = BeautifulSoup(r.text,'html.parser')
count=0
for a in soup.find_all('a', href=True):
    txt=a.get_text(separator=' ').strip()
    if 'IPL' in txt or 'Indian Premier' in txt or 'Indian' in txt:
        print(a['href'],'|', txt[:200].replace('\n',' '))
        count+=1
print('found:',count)
