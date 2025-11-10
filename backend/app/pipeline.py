# app/pipeline.py (excerpt)
import tldextract, trafilatura
from datetime import datetime
from .models import Article

def extract_domain(url:str)->str:
    t = tldextract.extract(url)
    return ".".join([p for p in [t.domain, t.suffix] if p])

def fetch_and_clean(url:str)->Article:
    downloaded = trafilatura.fetch_url(url)
    clean = trafilatura.extract(downloaded, include_comments=False, include_tables=False)
    art = Article(url=url, domain=extract_domain(url), clean_text=clean)
    return art
