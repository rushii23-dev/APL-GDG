import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict
import re

CRICBUZZ_LIVE_URL = "https://www.cricbuzz.com/cricket-match/live-scores"
CRICBUZZ_MOBILE = "https://m.cricbuzz.com/cricket-match/live-scores"
ESPN_LIVE = "https://www.espncricinfo.com/ci/engine/match/index.html?view=live"


def _find_ipl_match_link(soup: BeautifulSoup) -> Optional[str]:
    # Find anchors whose surrounding text mentions IPL and which link to a match page
    for a in soup.find_all('a', href=True):
        href = a['href']
        text = a.get_text(separator=' ').strip()
        if not href:
            continue
        if ('IPL' in text or 'Indian Premier' in text or 'Indian' in text) and ('/cricket-score' in href or '/live-cricket-score' in href or '/cricket-match' in href or '/match' in href):
            return 'https://www.cricbuzz.com' + href
    # Fallback: search for any anchor with 'IPL' in nearby text
    for tag in soup.find_all(text=re.compile(r'IPL|Indian Premier', re.I)):
        a = tag.find_parent('a')
        if a and a.get('href'):
            return 'https://www.cricbuzz.com' + a['href']
    return None


def _parse_score_and_overs(text: str) -> Dict[str, str]:
    # Look for patterns like '159/3 (15.2 ov)'
    res = {"score": "", "overs": "", "current_run_rate": ""}
    m = re.search(r"(\d{1,3}/\d{1,2})\s*\((\d{1,2}\.\d)\s*ov\)", text)
    if m:
        res['score'] = m.group(1)
        res['overs'] = m.group(2)
        return res
    # alternative pattern: '159/3 (15.2 overs)'
    m = re.search(r"(\d{1,3}/\d{1,2})\s*\((\d{1,2}\.\d)\s*overs?\)", text)
    if m:
        res['score'] = m.group(1)
        res['overs'] = m.group(2)
        return res
    # fallback: find first occurrence of X/Y
    m = re.search(r"(\d{1,3}/\d{1,2})", text)
    if m:
        res['score'] = m.group(1)
    m = re.search(r"(\d{1,2}\.\d)\s*ov", text)
    if m:
        res['overs'] = m.group(1)
    return res


def fetch_latest_ipl_live() -> Optional[Dict]:
    """Try to find a live IPL match and return structured fields.

    Returns a dict with keys used by the frontend. Returns None if not found.
    """
    # Try multiple sources: mobile Cricbuzz (faster), desktop Cricbuzz, then ESPN as fallback
    bodies = []
    for url in (CRICBUZZ_MOBILE, CRICBUZZ_LIVE_URL, ESPN_LIVE):
        try:
            resp = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            bodies.append((url, resp.text))
        except Exception:
            continue
    if not bodies:
        return None

    # From the list of fetched bodies, find a likely match link and then fetch that match page
    match_link = None
    match_body = None
    for url, body in bodies:
        s = BeautifulSoup(body, "html.parser")
        l = _find_ipl_match_link(s)
        if l:
            match_link = l
            match_body = None
            break

    # If we found a match link, fetch it. Otherwise, try to parse score directly from any fetched page.
    msoup = None
    if match_link:
        try:
            mresp = requests.get(match_link, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
            mresp.raise_for_status()
            msoup = BeautifulSoup(mresp.text, "html.parser")
        except Exception:
            msoup = None

    meta_text = ''
    match_title = match_link or ''
    if msoup:
        og = msoup.find('meta', property='og:title') or msoup.find('meta', attrs={'name': 'description'}) or msoup.find('meta', property='og:description')
        if og and og.get('content'):
            meta_text = og.get('content')
        else:
            title = msoup.find('title')
            meta_text = title.get_text().strip() if title else msoup.get_text(separator=' ', strip=True)
            match_title = title.get_text().strip() if title else match_title
    else:
        # fallback: search all fetched bodies for a score-like snippet
        for url, body in bodies:
            m = re.search(r"\d{1,3}/\d{1,2}\s*\(\d{1,2}\.\d\s*ov", body)
            if m:
                meta_text = body[m.start()-80:m.end()+80]
                match_title = url
                break
        if not meta_text and bodies:
            # last resort: use the first body's title or content
            s0 = BeautifulSoup(bodies[0][1], "html.parser")
            t0 = s0.find('title')
            meta_text = t0.get_text().strip() if t0 else s0.get_text(separator=' ', strip=True)[:400]

    parsed = _parse_score_and_overs(meta_text)

    # Attempt to extract match title more readably
    try:
        if msoup and msoup.find('title'):
            full_title = msoup.find('title').get_text() or ''
            if '|' in full_title:
                match_title = full_title.split('|')[-1].strip()
            else:
                match_title = full_title
    except Exception:
        pass

    # Ensure overs don't exceed 20 for T20 matches
    overs = parsed.get('overs', '')
    try:
        if overs:
            ov_val = float(overs)
            if ov_val > 20.0:
                overs = '20.0'
    except Exception:
        pass

    # Try to capture striker and bowler names heuristically from description
    striker = ''
    bowler = ''
    m_striker = re.search(r"([A-Z][a-zA-Z.'\- ]{2,30})\s*\(\d+\*?\)", meta_text)
    if m_striker:
        striker = m_striker.group(1).strip()

    # Return a minimal structured payload used by the frontend
    return {
        'match': match_title,
        'venue': '',
        'batting_team': '',
        'bowling_team': '',
        'score': parsed.get('score', ''),
        'overs': overs,
        'striker': striker,
        'non_striker': '',
        'bowler': bowler,
        'target': '',
        'current_run_rate': parsed.get('current_run_rate', ''),
    }
