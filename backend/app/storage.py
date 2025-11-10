# app/storage.py (source prior)
from .models import Source
from sqlmodel import Session, select

def get_or_seed_source(session: Session, domain:str) -> Source:
    src = session.exec(select(Source).where(Source.domain==domain)).first()
    if not src:
        src = Source(domain=domain, name=domain, bayes_prior_truth=0.6)
        session.add(src); session.commit()
    return src
