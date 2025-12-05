CLAIM_EXTRACTION_PROMPT = """You are a helpful assistant that extracts factual claims from the given url or text.

A "claim" is a statement that makes a factual assertion about reality. 
- Include specific numbers, statistics, dates, attributions
- Include opinions, predictions
- Include questions
- Exclude editorial comments, common knowledge

Text: "{text}"

EXAMPLES OF WHAT TO EXTRACT:
- "The vaccine was developed in 6 months" (specific timeframe)
- "Masks reduce transmission by 50%" (quantified assertion)
- "According to WHO, COVID originated in 2019" (attributed claim)
- "I believe the vaccine is safe" (opinion)
- "Will inflation improve next year?" (question/prediction)

EXAMPLES OF WHAT NOT TO EXTRACT:
- "The sky is blue" (common knowledge)
- "This is an important discovery" (editorial comment)

Return ONLY a valid JSON array (no markdown, no explanation):
[
  {{
    "claim": "exact text from the article",
    "start_char": 0,
    "end_char": 50,
    "topic": "vaccine|pandemic|election|economy|etc"
  }},
  ...
]

If no claims found, return: This claim seems to be an opinion or does not contain factual assertions.
"""

STANCE_DETECTION_PROMPT = """You are a helpful assistant that determines the stance of a claim based on provided evidence.

Statement: "{claim}"
Source text: "{evidence}"

Does the source text support, contradict, or neither relate to the statement?

Respond with one word: "support", "contradict", or "neither"
"""

SIMILARITY_SCORING_PROMPT = """On a scale from 0 to 1.0, how relevant is the source text to the statement?

Statement: "{claim}"
Source text: "{evidence}"

Respond with only a number from 0 to 1.0
"""