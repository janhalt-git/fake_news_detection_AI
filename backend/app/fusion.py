# app/fusion.py
import math
from typing import Tuple

def logit(p: float, eps: float=1e-6) -> float:
    p = min(max(p, eps), 1-eps)
    return math.log(p/(1-p))

def sigmoid(z: float) -> float:
    return 1/(1+math.exp(-z))

def combine_confidence(source_prior: float, text_consistency: float, cross_reference: float,
                       w_source: float=0.4, w_text: float=0.4, w_cross: float=0.6) -> Tuple[float,str]:
    # Normalize weights so they sum to 1
    s = w_source + w_text + w_cross
    ws, wt, wc = w_source/s, w_text/s, w_cross/s
    z = ws*logit(source_prior) + wt*logit(text_consistency) + wc*logit(cross_reference)
    conf = sigmoid(z)
    # Simple verdict thresholds (tune as needed)
    if conf >= 0.7: verdict = "Likely true"
    elif conf >= 0.45: verdict = "Uncertain"
    else: verdict = "Likely misleading"
    explanation = (
        f"Combined via weighted log-odds: source={source_prior:.2f}, "
        f"text={text_consistency:.2f}, cross-ref={cross_reference:.2f} → {conf:.2f} ({verdict})."
    )
    return conf, explanation
