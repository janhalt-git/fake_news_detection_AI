# app/main.py
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel, Session, create_engine

from .schema import AnalyzeRequest, AnalyzeResponse, ClaimOut, EvidenceOut
from .pipeline import fetch_and_clean, extract_domain
from .storage import get_or_seed_source
from .fusion import combine_confidence
from .models import Article, Claim, Evidence, Verification

# Configure logging to show DEBUG level
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

engine = create_engine("sqlite:///./verifier.db", echo=False)
SQLModel.metadata.create_all(engine)

app = FastAPI(title="FakeNews Verifier API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (you can restrict this to specific domains later)
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    if not req.url and not req.text:
        raise HTTPException(400, "Provide url or text")

    with Session(engine) as session:
        # Ingest & Clean
        if req.url:
            article = fetch_and_clean(req.url)
        else:
            article = Article(clean_text=req.text)
        article.domain = article.domain or (extract_domain(req.url) if req.url else None)
        session.add(article); session.commit(); session.refresh(article)

        # Source prior
        source_prior = 0.5
        if article.domain:
            src = get_or_seed_source(session, article.domain)
            source_prior = src.bayes_prior_truth

        # Claims + evidence + text consistency
        from .clients.claims_client import extract_claims_and_evidence
        ce = extract_claims_and_evidence(article.clean_text or "")

        text_consistency = float(ce.get("text_consistency", 0.5))
        cross_reference = float(ce.get("cross_reference", 0.0))

        # Check if no cross-references found
        if cross_reference == 0.0:
            combined = -1.0
            explanation = "Insufficient data: No fact-check cross-references found for any claims."
            verdict = "Insufficient data"
        else:
            # Fusion
            combined, explanation = combine_confidence(source_prior, text_consistency, cross_reference)
            verdict = "Likely true" if combined>=0.7 else ("Uncertain" if combined>=0.45 else "Likely misleading")

        # Persist minimal
        ver = Verification(article_id=article.id, source_prior=source_prior,
                           text_consistency=text_consistency, cross_reference=cross_reference,
                           combined_confidence=combined, explanation=explanation)
        session.add(ver); session.commit()

        # Claims/Evidence persistence
        claims_out = []
        for c in ce.get("claims", []):
            claim_row = Claim(article_id=article.id, text=c["text"],
                              start_char=c.get("start_char"), end_char=c.get("end_char"))
            session.add(claim_row); session.commit(); session.refresh(claim_row)
            ev_outs = []
            for ev in c.get("evidences", []):
                ev_row = Evidence(claim_id=claim_row.id, **ev)
                session.add(ev_row); session.commit()
                ev_outs.append(EvidenceOut(**ev))
            claims_out.append(ClaimOut(text=c["text"],
                                       start_char=c.get("start_char"), end_char=c.get("end_char"),
                                       evidences=ev_outs))

        return AnalyzeResponse(
            domain=article.domain, source_prior=source_prior,
            text_consistency=text_consistency, cross_reference=cross_reference,
            combined_confidence=combined, verdict_label=verdict,
            explanation=explanation, claims=claims_out
        )
