"""Render the homepage's sample site (English and Hindi) through the real site template.

The content is written by hand, so this makes no Claude call. It goes through the same
SiteContent model, content check and template as a generated site, so the sample shows
exactly what Shuru produces. Run from `backend/`:

    .venv/bin/python -m scripts.render_samples
"""

from pathlib import Path

from app.models import Lang, SiteContent
from app.services.content_check import find_problems
from app.services.site_service import SiteService

DOMAIN = "lucknowachaar.com"
OUT_DIR = Path(__file__).resolve().parents[2] / "frontend" / "public" / "samples"


def t(en: str, hi: str) -> dict[str, str]:
    return {"en": en, "hi": hi}


SAMPLE = SiteContent.model_validate(
    {
        "hero": {
            "headline": t("Homemade achaar from Lucknow", "लखनऊ का घर का बना अचार"),
            "subheadline": t(
                "Small-batch pickles made the way our grandmother taught us, sun-cured and full of flavour.",
                "छोटे-छोटे बैच में, दादी माँ के तरीके से धूप में तैयार किया गया, स्वाद से भरपूर अचार।",
            ),
        },
        "offer": {
            "heading": t("What we make", "हम क्या बनाते हैं"),
            "items": [
                t("Raw mango achaar in mustard oil", "सरसों के तेल में कच्चे आम का अचार"),
                t("Sweet and tangy lemon achaar", "खट्टा-मीठा नींबू का अचार"),
                t("Spicy green chilli achaar", "तीखा हरी मिर्च का अचार"),
                t("Mixed vegetable achaar for every meal", "हर खाने के लिए मिक्स सब्ज़ी का अचार"),
            ],
        },
        "about": {
            "heading": t("Our story", "हमारी कहानी"),
            "body": t(
                "We started in our home kitchen in Lucknow with one family recipe. Every jar is still filled "
                "by hand, with whole spices and no preservatives.",
                "हमने लखनऊ में अपनी घर की रसोई से, परिवार की एक पुरानी विधि के साथ शुरुआत की। आज भी हर "
                "बरनी हाथ से भरी जाती है, साबुत मसालों के साथ और बिना किसी प्रिज़र्वेटिव के।",
            ),
        },
        "faq": [
            {
                "question": t("How long does the achaar keep?", "अचार कितने दिन चलता है?"),
                "answer": t(
                    "Up to a year in a cool, dry place. Always use a dry spoon.",
                    "ठंडी और सूखी जगह पर एक साल तक। हमेशा सूखे चम्मच का इस्तेमाल करें।",
                ),
            },
            {
                "question": t("Do you deliver outside Lucknow?", "क्या आप लखनऊ के बाहर भी भेजते हैं?"),
                "answer": t(
                    "Yes, we ship across India in sealed glass jars.",
                    "हाँ, हम पूरे भारत में सील बंद काँच की बरनियों में भेजते हैं।",
                ),
            },
            {
                "question": t("Can I order a gift box?", "क्या मैं गिफ़्ट बॉक्स मँगवा सकता हूँ?"),
                "answer": t(
                    "Yes, we pack festive gift boxes with three jars of your choice.",
                    "हाँ, हम आपकी पसंद की तीन बरनियों वाला त्योहार का गिफ़्ट बॉक्स बनाते हैं।",
                ),
            },
        ],
        "contact": {
            "heading": t("Get in touch", "संपर्क करें"),
            "text": t(
                "Message us to place an order or ask about bulk and festive orders.",
                "ऑर्डर देने या थोक और त्योहार के ऑर्डर के बारे में पूछने के लिए हमें संदेश भेजें।",
            ),
        },
    }
)


def main() -> None:
    problems = find_problems(SAMPLE, allowed_domains=[DOMAIN])
    if problems:
        raise SystemExit("Sample content fails the content check: " + "; ".join(problems))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    service = SiteService()
    for lang in Lang:
        path = OUT_DIR / f"sample-site.{lang.value}.html"
        path.write_text(service.render(SAMPLE, DOMAIN, lang), encoding="utf-8")
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
