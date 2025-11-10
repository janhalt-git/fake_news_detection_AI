# app/tests/test_fusion.py
from backend.app.fusion import combine_confidence

def test_fusion_refuted_claims_low_confidence():
    conf, _ = combine_confidence(source_prior=0.6, text_consistency=0.4, cross_reference=0.1)
    assert conf < 0.45  # likely misleading

def test_fusion_supportive_high_confidence():
    conf, _ = combine_confidence(source_prior=0.8, text_consistency=0.8, cross_reference=0.7)
    assert conf >= 0.7  # likely true
