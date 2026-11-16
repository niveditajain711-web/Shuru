from app.models import Lang

_LANGUAGE_NAMES = {Lang.EN: "English", Lang.HI: "Hindi (Devanagari script)"}

_JSON_RULES = (
    "Reply with a single JSON object and nothing else: no markdown, no code fences, no commentary. "
    "The JSON must match this JSON Schema exactly:\n"
)

BRIEF_SYSTEM = (
    "You help first-time founders turn a one-sentence business idea into a short brief. "
    "Write `audience`, `tone` and `tagline` in the requested language. "
    "`name_ideas` are 8 to 10 short, memorable brand names that suit the idea. Each one must be "
    "lowercase Latin letters, digits or hyphens only (no spaces, no dots, no top-level domain), "
    "so it can be searched as a domain name.\n" + _JSON_RULES
)

SITE_SYSTEM = (
    "You write the content for a one-page website for a small business. "
    "Every text field has an `en` and a `hi` value. Write each language natively, from the brief, "
    "as a fluent local writer would. Do not translate one language into the other, and avoid "
    "literal, word-for-word phrasing. Hindi must be in Devanagari script. "
    "Both languages must state the same facts. Do not invent phone numbers, email addresses, "
    "street addresses, prices, certifications or statistics; in `contact`, tell visitors to get in "
    "touch through the channel the owner will add later, without naming one.\n" + _JSON_RULES
)


def brief_user_message(idea: str, lang: Lang) -> str:
    return f"Business idea: {idea}\nWrite the brief in {_LANGUAGE_NAMES[lang]}."


def site_user_message(brief_json: str, domain: str) -> str:
    return f"Website domain: {domain}\nBrief:\n{brief_json}"
