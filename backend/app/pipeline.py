# app/pipeline.py
import tldextract, trafilatura
import logging
from datetime import datetime
from .models import Article

logger = logging.getLogger(__name__)

def extract_domain(url: str) -> str:
    url = str(url)  # Convert to string - handles HttpUrl objects from Pydantic
    logger.debug(f"Extracting domain from URL: {url}")
    t = tldextract.extract(url)
    domain = ".".join([p for p in [t.domain, t.suffix] if p])
    logger.debug(f"Extracted domain: {domain}")
    return domain

def fetch_and_clean(url: str) -> Article:
    url = str(url)  # Convert to string - handles HttpUrl objects from Pydantic
    logger.info(f"Fetching URL: {url}")
    downloaded = trafilatura.fetch_url(url)
    logger.info(f"Downloaded content length: {len(downloaded) if downloaded else 0} bytes")
    clean = trafilatura.extract(downloaded, include_comments=False, include_tables=False)
    logger.info(f"Extracted clean text length: {len(clean) if clean else 0} characters")
    logger.debug(f"Clean text preview: {clean[:200] if clean else 'None'}")
    art = Article(url=url, domain=extract_domain(url), clean_text=clean)
    return art
