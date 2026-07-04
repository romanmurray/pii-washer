import json
import re
from pathlib import Path

import tldextract
import tldextract.tldextract as _tldextract_mod
from presidio_analyzer import AnalyzerEngine, EntityRecognizer, Pattern, PatternRecognizer, RecognizerResult
from presidio_analyzer.nlp_engine import NlpEngineProvider

# Force tldextract to use its bundled snapshot only — no network calls.
# Presidio's EmailRecognizer calls tldextract.extract() which would otherwise
# fetch the Public Suffix List over HTTPS on first use.
_tldextract_mod.TLD_EXTRACTOR = tldextract.TLDExtract(
    suffix_list_urls=(),
    fallback_to_snapshot=True,
)

DATA_DIR = Path(__file__).parent / "data"


# ---------------------------------------------------------------------------
# SSN custom recognizer
# ---------------------------------------------------------------------------

def _luhn_check(number_str: str) -> bool:
    digits = [int(d) for d in number_str]
    checksum = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0


def _ssn_valid(area: str, group: str, serial: str) -> bool:
    """SSA validation rules: invalid area/group/serial combos."""
    if area in ("000", "666") or area.startswith("9"):
        return False
    if group == "00":
        return False
    if serial == "0000":
        return False
    return True


class CustomSSNRecognizer(EntityRecognizer):
    """Custom SSN recognizer supporting dashes, spaces, dots, mixed, no-separator."""

    SSN_CONTEXT_KEYWORDS = [
        "ssn", "social security", "social sec", "ss#", "ss #",
        "taxpayer id", "tax id",
    ]
    SSN_CONTEXT_WINDOW = 100
    CONTEXT_BOOST = 0.2

    def __init__(self):
        super().__init__(
            supported_entities=["US_SSN"],
            supported_language="en",
            name="CustomSSNRecognizer",
        )

    def load(self):
        pass

    def _has_ssn_context(self, text: str, span_start: int) -> bool:
        window_start = max(0, span_start - self.SSN_CONTEXT_WINDOW)
        context = text[window_start:span_start + self.SSN_CONTEXT_WINDOW].lower()
        return any(kw in context for kw in self.SSN_CONTEXT_KEYWORDS)

    def analyze(self, text, entities, nlp_artifacts=None, regex_flags=0):
        results = []
        seen = set()

        # Dashed: consistent separator (highest confidence for dashes specifically)
        for m in re.finditer(r"\b(\d{3})-(\d{2})-(\d{4})\b", text):
            area, group, serial = m.group(1), m.group(2), m.group(3)
            if not _ssn_valid(area, group, serial):
                continue
            span = (m.start(), m.end())
            if span not in seen:
                seen.add(span)
                score = 0.85
                if self._has_ssn_context(text, m.start()):
                    score = min(1.0, score + self.CONTEXT_BOOST)
                results.append(RecognizerResult("US_SSN", m.start(), m.end(), score))

        # Spaced: same separator (spaces)
        for m in re.finditer(r"\b(\d{3}) (\d{2}) (\d{4})\b", text):
            area, group, serial = m.group(1), m.group(2), m.group(3)
            if not _ssn_valid(area, group, serial):
                continue
            span = (m.start(), m.end())
            if span not in seen:
                seen.add(span)
                score = 0.7
                if self._has_ssn_context(text, m.start()):
                    score = min(1.0, score + self.CONTEXT_BOOST)
                results.append(RecognizerResult("US_SSN", m.start(), m.end(), score))

        # Dotted: same separator (dots)
        for m in re.finditer(r"\b(\d{3})\.(\d{2})\.(\d{4})\b", text):
            area, group, serial = m.group(1), m.group(2), m.group(3)
            if not _ssn_valid(area, group, serial):
                continue
            span = (m.start(), m.end())
            if span not in seen:
                seen.add(span)
                score = 0.65
                if self._has_ssn_context(text, m.start()):
                    score = min(1.0, score + self.CONTEXT_BOOST)
                results.append(RecognizerResult("US_SSN", m.start(), m.end(), score))

        # Mixed separators (any combination)
        for m in re.finditer(r"\b(\d{3})[\s.\-](\d{2})[\s.\-](\d{4})\b", text):
            area, group, serial = m.group(1), m.group(2), m.group(3)
            if not _ssn_valid(area, group, serial):
                continue
            span = (m.start(), m.end())
            if span not in seen:
                seen.add(span)
                score = 0.6
                if self._has_ssn_context(text, m.start()):
                    score = min(1.0, score + self.CONTEXT_BOOST)
                results.append(RecognizerResult("US_SSN", m.start(), m.end(), score))

        # No separator: only with context
        for m in re.finditer(r"\b(\d{3})(\d{2})(\d{4})\b", text):
            area, group, serial = m.group(1), m.group(2), m.group(3)
            if not _ssn_valid(area, group, serial):
                continue
            if not self._has_ssn_context(text, m.start()):
                continue
            span = (m.start(), m.end())
            if span not in seen:
                seen.add(span)
                results.append(RecognizerResult("US_SSN", m.start(), m.end(), 0.4))

        return results


# ---------------------------------------------------------------------------
# Phone number custom recognizer
# ---------------------------------------------------------------------------

class CustomPhoneRecognizer(EntityRecognizer):
    """Custom phone recognizer for dots, spaces, no-separator, mixed, country code, ext."""

    PHONE_CONTEXT_KEYWORDS = [
        "call", "phone", "tel", "cell", "mobile", "fax",
        "contact", "dial", "reach", "phone number", "tel:",
    ]
    PHONE_CONTEXT_WINDOW = 100

    _EXTENSION = r"(?:\s*(?:ext|x|extension)\.?\s*\d{1,5})?"

    def __init__(self):
        super().__init__(
            supported_entities=["PHONE_NUMBER"],
            supported_language="en",
            name="CustomPhoneRecognizer",
        )

    def load(self):
        pass

    def _has_phone_context(self, text: str, span_start: int) -> bool:
        window_start = max(0, span_start - self.PHONE_CONTEXT_WINDOW)
        context = text[window_start:span_start + self.PHONE_CONTEXT_WINDOW].lower()
        return any(kw in context for kw in self.PHONE_CONTEXT_KEYWORDS)

    def analyze(self, text, entities, nlp_artifacts=None, regex_flags=0):
        results = []
        seen = set()

        # Area code first digit is always 2-9 (NANP) — a strong anti-false-positive
        # signal. The exchange digit is relaxed to \d only for parenthesized formats:
        # the parens make "(555) 123-4567" unmistakably a phone number, and that
        # example exchange (starting with 1) is the most common one users paste.
        # Bare-separator formats keep the strict exchange to avoid matching dates/IDs.
        patterns = [
            # Parentheses + dashes: (555) 123-4567 (0.75) — very common US format
            (r"\(([2-9]\d{2})\)\s*\d{3}-\d{4}" + self._EXTENSION, 0.75),
            # Country code + parens: +1 (555) 123-4567 (0.75)
            (r"\+?1\s*\(([2-9]\d{2})\)\s*\d{3}-\d{4}" + self._EXTENSION, 0.75),
            # Dashes: 555-234-5678 (0.65) — standard format
            (r"\b([2-9]\d{2})-[2-9]\d{2}-\d{4}" + self._EXTENSION + r"\b", 0.65),
            # Country code + dashes: +1-555-234-5678 (0.7)
            (r"\+1[\s.\-]([2-9]\d{2})[\s.\-][2-9]\d{2}[\s.\-]\d{4}" + self._EXTENSION, 0.7),
            # Dots: 512.555.1234 (0.65)
            (r"\b([2-9]\d{2})\.[2-9]\d{2}\.\d{4}" + self._EXTENSION + r"\b", 0.65),
            # Spaces: 512 555 1234 (0.55)
            (r"\b([2-9]\d{2}) [2-9]\d{2} \d{4}" + self._EXTENSION + r"\b", 0.55),
            # Mixed: (512) 555.1234 or (512) 555 1234 (0.65)
            (r"\(([2-9]\d{2})\)\s*\d{3}[.\s]\d{4}" + self._EXTENSION, 0.65),
        ]

        for pat, base_score in patterns:
            for m in re.finditer(pat, text):
                span = (m.start(), m.end())
                if span not in seen:
                    seen.add(span)
                    results.append(RecognizerResult("PHONE_NUMBER", m.start(), m.end(), base_score))

        # No separators: only with context (0.4)
        no_sep_pat = re.compile(r"\b([2-9]\d{2})([2-9]\d{2})\d{4}\b")
        for m in no_sep_pat.finditer(text):
            span = (m.start(), m.end())
            if span not in seen and self._has_phone_context(text, m.start()):
                seen.add(span)
                results.append(RecognizerResult("PHONE_NUMBER", m.start(), m.end(), 0.4))

        return results


# ---------------------------------------------------------------------------
# Credit card recognizer with Luhn
# ---------------------------------------------------------------------------

class CustomCreditCardRecognizer(EntityRecognizer):
    """Custom CCN recognizer with Luhn validation for spaces, dashes, no-sep, dots.

    Numbers that fail Luhn but sit near card context words ("card", "cvv",
    "expiration"…) are still flagged at 0.5 — fake/test numbers and typos
    must not slip through half-redacted."""

    CARD_CONTEXT_KEYWORDS = [
        "card", "credit", "debit", "visa", "mastercard", "amex",
        "discover", "expir", "cvv", "cvc", "payment",
    ]
    CARD_CONTEXT_WINDOW = 100
    NON_LUHN_WITH_CONTEXT_SCORE = 0.5

    def __init__(self):
        super().__init__(
            supported_entities=["CREDIT_CARD"],
            supported_language="en",
            name="CustomCreditCardRecognizer",
        )

    def load(self):
        pass

    def _has_card_context(self, text: str, span_start: int) -> bool:
        window_start = max(0, span_start - self.CARD_CONTEXT_WINDOW)
        context = text[window_start:span_start + self.CARD_CONTEXT_WINDOW].lower()
        return any(kw in context for kw in self.CARD_CONTEXT_KEYWORDS)

    def analyze(self, text, entities, nlp_artifacts=None, regex_flags=0):
        results = []
        seen = set()

        patterns = [
            # Spaces: 4111 1111 1111 1111 (0.75)
            (r"\b(\d{4}) (\d{4}) (\d{4}) (\d{4})\b", 0.75),
            # Dashes: 4111-1111-1111-1111 (0.7)
            (r"\b(\d{4})-(\d{4})-(\d{4})-(\d{4})\b", 0.7),
            # Dots: 4111.1111.1111.1111 (0.6)
            (r"\b(\d{4})\.(\d{4})\.(\d{4})\.(\d{4})\b", 0.6),
            # No separators: 4111111111111111 (0.5)
            (r"\b(\d{16})\b", 0.5),
        ]

        for pat, score in patterns:
            for m in re.finditer(pat, text):
                digits = re.sub(r"\D", "", m.group())
                if _luhn_check(digits):
                    effective_score = score
                elif self._has_card_context(text, m.start()):
                    effective_score = self.NON_LUHN_WITH_CONTEXT_SCORE
                else:
                    continue
                span = (m.start(), m.end())
                if span not in seen:
                    seen.add(span)
                    results.append(RecognizerResult("CREDIT_CARD", m.start(), m.end(), effective_score))

        return results


# ---------------------------------------------------------------------------
# IP address enhancement (IPv6, IPv4+port)
# ---------------------------------------------------------------------------

class CustomIPRecognizer(EntityRecognizer):
    """Detects IPv4+port, full IPv6, and compressed IPv6."""

    def __init__(self):
        super().__init__(
            supported_entities=["IP_ADDRESS"],
            supported_language="en",
            name="CustomIPRecognizer",
        )

    def load(self):
        pass

    def analyze(self, text, entities, nlp_artifacts=None, regex_flags=0):
        results = []
        seen = set()

        # IPv4 with port
        ipv4_port = re.compile(
            r"\b(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3}):(\d{1,5})\b"
        )
        for m in ipv4_port.finditer(text):
            octets = (int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)))
            port = int(m.group(5))
            if any(o > 255 for o in octets) or port < 1 or port > 65535:
                continue
            span = (m.start(), m.end())
            if span not in seen:
                seen.add(span)
                results.append(RecognizerResult("IP_ADDRESS", m.start(), m.end(), 0.65))

        # Full IPv6: 8 groups of 1-4 hex digits
        ipv6_full = re.compile(
            r"\b([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b"
        )
        for m in ipv6_full.finditer(text):
            addr = m.group().lower()
            # Exclude loopback (handled in post-filter too)
            if addr == "0:0:0:0:0:0:0:1":
                continue
            span = (m.start(), m.end())
            if span not in seen:
                seen.add(span)
                results.append(RecognizerResult("IP_ADDRESS", m.start(), m.end(), 0.7))

        # Compressed IPv6 with ::
        ipv6_compressed = re.compile(
            r"\b(?:[0-9a-fA-F]{1,4}:)*::(?:[0-9a-fA-F]{1,4}:)*[0-9a-fA-F]{1,4}\b"
            r"|\b::(?:[0-9a-fA-F]{1,4}:)*[0-9a-fA-F]{1,4}\b"
            r"|\b(?:[0-9a-fA-F]{1,4}:)+:\b"
        )
        for m in ipv6_compressed.finditer(text):
            addr = m.group().lower()
            # Exclude loopback ::1 and link-local fe80::
            if addr == "::1" or addr.startswith("fe80::"):
                continue
            span = (m.start(), m.end())
            if span not in seen:
                seen.add(span)
                results.append(RecognizerResult("IP_ADDRESS", m.start(), m.end(), 0.65))

        return results


# ---------------------------------------------------------------------------
# Obfuscated email recognizer
# ---------------------------------------------------------------------------

class ObfuscatedEmailRecognizer(PatternRecognizer):
    """Detects obfuscated email patterns like user[at]domain or user@domain[dot]com."""

    def __init__(self):
        patterns = [
            Pattern(
                "obfuscated_at",
                r"[a-zA-Z0-9._%+\-]+\s*[\[\(]at[\]\)]\s*[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
                score=0.5,
            ),
            Pattern(
                "obfuscated_dot",
                r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\s*[\[\(]dot[\]\)]\s*[a-zA-Z]{2,}",
                score=0.5,
            ),
        ]
        super().__init__(
            supported_entity="EMAIL_ADDRESS",
            patterns=patterns,
            supported_language="en",
            name="ObfuscatedEmailRecognizer",
        )


# ---------------------------------------------------------------------------
# PO Box recognizer
# ---------------------------------------------------------------------------

class POBoxRecognizer(PatternRecognizer):
    """Detects PO Box addresses."""

    def __init__(self):
        patterns = [
            Pattern(
                "po_box",
                r"\b(?:P\.?O\.?\s*Box|POB|Post\s+Office\s+Box)\s+\d+\b",
                score=0.7,
            ),
        ]
        super().__init__(
            supported_entity="US_PO_BOX",
            patterns=patterns,
            supported_language="en",
            name="POBoxRecognizer",
        )


# ---------------------------------------------------------------------------
# Labeled identifier recognizer
# ---------------------------------------------------------------------------

class LabeledIdentifierRecognizer(EntityRecognizer):
    """Catches identifiers by their label: "Routing number: 071923284".

    Bare codes like EMP-104928 are too ambiguous to tag on shape alone —
    matching them everywhere would flood real text with false positives.
    But when the text labels the value, the label is a high-confidence
    signal. Covers financial, government-ID, insurance, vehicle, and
    organization-internal identifiers.
    """

    # ponytail: flat keyword list + colon + code-shaped value. No per-format
    # validation (routing checksums, passport formats) — the label does the work.
    LABEL_KEYWORDS = [
        "routing", "account number", "account no", "acct",
        "cvv", "cvc", "security code",
        "driver license", "driver's license", "drivers license",
        "license number", "license no", "license plate", "plate",
        "passport",
        "member id", "member number", "group number", "group no",
        "policy number", "policy no",
        "employee id", "customer id", "order number", "order no",
        "reference number", "case number",
        "expiration", "expiry",
    ]

    # "<label> <up to 25 filler chars>: <code>" — code must start/end alphanumeric
    _PATTERN = re.compile(
        r"\b(?:" + "|".join(re.escape(kw) for kw in LABEL_KEYWORDS) + r")"
        r"[^:\n]{0,25}:[ \t]*"
        r"([A-Za-z0-9](?:[A-Za-z0-9\-\/\.]{0,29}[A-Za-z0-9])?)",
        re.IGNORECASE,
    )

    def __init__(self):
        super().__init__(
            supported_entities=["LABELED_ID"],
            supported_language="en",
            name="LabeledIdentifierRecognizer",
        )

    def load(self):
        pass

    def analyze(self, text, entities, nlp_artifacts=None, regex_flags=0):
        results = []
        for m in self._PATTERN.finditer(text):
            value = m.group(1)
            # Prose after a label ("Account note: pending review") isn't an ID
            if not any(c.isdigit() for c in value):
                continue
            results.append(RecognizerResult("LABELED_ID", m.start(1), m.end(1), 0.7))
        return results


# ---------------------------------------------------------------------------
# Main engine
# ---------------------------------------------------------------------------

class PIIDetectionEngine:
    VALID_CATEGORIES = ["NAME", "ADDRESS", "PHONE", "EMAIL", "SSN", "DOB", "CCN", "IP", "URL", "ID"]

    ENTITY_MAPPING = {
        "PERSON": "NAME",
        "LOCATION": "ADDRESS",
        "PHONE_NUMBER": "PHONE",
        "EMAIL_ADDRESS": "EMAIL",
        "US_SSN": "SSN",
        "CREDIT_CARD": "CCN",
        "IP_ADDRESS": "IP",
        "DATE_TIME": "DOB",
        "URL": "URL",
        "US_STREET_ADDRESS": "ADDRESS",
        "US_ZIP_CODE": "ADDRESS",
        "US_PO_BOX": "ADDRESS",
        "LABELED_ID": "ID",
    }

    US_STREET_TYPES = [
        "Street", "St", "Avenue", "Ave", "Boulevard", "Blvd",
        "Drive", "Dr", "Lane", "Ln", "Road", "Rd", "Court", "Ct",
        "Place", "Pl", "Way", "Circle", "Cir", "Terrace", "Ter",
        "Trail", "Trl", "Parkway", "Pkwy", "Highway", "Hwy",
        "Route", "Rte",
    ]

    US_STATE_ABBREVIATIONS = [
        "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
        "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
        "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
        "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
        "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
        "DC",
    ]

    # Expanded window and keywords
    ZIP_CONTEXT_WINDOW = 150
    ZIP_CONTEXT_KEYWORDS = ["zip", "zip code", "postal", "postal code"]

    # Expanded DOB keywords and window
    DOB_CONTEXT_KEYWORDS = [
        "born", "birth", "birthday", "dob", "date of birth",
        "birth date", "birthdate", "age",
        "d.o.b", "b.", "born on", "birth year",
    ]
    DOB_CONTEXT_WINDOW = 100  # Widened from 50

    # Expanded URL patterns
    PII_URL_PATTERNS = [
        "linkedin.com/in/",
        "facebook.com/",
        "github.com/",
        "twitter.com/",
        "x.com/",
        "instagram.com/",
        "reddit.com/user/",
        "reddit.com/u/",
        "tiktok.com/@",
        "medium.com/@",
        "youtube.com/@",
        "youtube.com/channel/",
        "pinterest.com/",
        "tumblr.com/",
        "mastodon.social/@",
        "threads.net/@",
        "bsky.app/profile/",
        "stackoverflow.com/users/",
        "gitlab.com/",
        "bitbucket.org/",
    ]

    # Profile path heuristic — non-PII path segments to exclude
    _PROFILE_PATH_EXCLUSIONS = {
        "settings", "update", "edit", "delete", "admin", "login",
        "logout", "signup", "register", "search", "explore", "trending",
        "notifications", "messages", "help", "about", "terms", "privacy",
    }

    # Build the street type alternation from the constant list
    _street_types_pattern = "|".join(US_STREET_TYPES)

    # Full street address pattern (added apt/suite suffix)
    US_STREET_ADDRESS_PATTERN = (
        r"\b\d{1,5}\s+"                                    # House number
        r"(?:(?:N|S|E|W|North|South|East|West|NE|NW|SE|SW)\.?\s+)?"  # Optional directional
        r"(?:[A-Z][a-zA-Z]*\.?\s+){1,4}"                  # Street name (1-4 words)
        r"(?:" + _street_types_pattern + r")\.?"           # Street type suffix
        r"(?:,?\s+(?:Apt|Apartment|Suite|Ste|Unit|#)\.?\s*\w+)?"  # Optional apt/suite (comma allowed)
        r"\b"
    )

    # Misspelled street types pattern
    _MISSPELLED_STREET_PATTERN = (
        r"\b\d{1,5}\s+"
        r"(?:(?:N|S|E|W|North|South|East|West|NE|NW|SE|SW)\.?\s+)?"
        r"(?:[A-Z][a-zA-Z]*\.?\s+){1,4}"
        r"(?:Steet|Stret|Avnue|Aveneue|Bulevard|Bouelvard)\.?"
        r"\b"
    )

    # Highway pattern
    _HIGHWAY_PATTERN = r"\b\d{1,5}\s+(?:Highway|Hwy|Route|Rte)\s+\d+\b"

    # State abbreviation + zip ("IL 62704") — captures the state, which nothing
    # else does. (?-i:) keeps it case-sensitive under Presidio's IGNORECASE
    # default so prose like "in 46201 samples" can't match.
    _STATE_ZIP_PATTERN = (
        r"\b(?-i:(?:" + "|".join(US_STATE_ABBREVIATIONS) + r"))"
        r"\s+\d{5}(?:-\d{4})?\b"
    )

    # Zip code patterns
    ZIP_PLUS_4_PATTERN = r"\b\d{5}-\d{4}\b"  # e.g., 62704-1234
    ZIP_5_PATTERN = r"\b\d{5}\b"  # e.g., 62704

    # Lower default threshold
    DEFAULT_CONFIDENCE_THRESHOLD = 0.2

    def __init__(self, model_name: str = "en_core_web_lg") -> None:
        provider = NlpEngineProvider(nlp_configuration={
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": model_name}],
        })
        nlp_engine = provider.create_engine()
        self._analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["en"])

        # Load city list for ZIP context — pre-compile as single alternation
        cities_path = DATA_DIR / "us_cities_top200.json"
        with open(cities_path, encoding="utf-8") as f:
            cities = json.load(f)
        self._us_cities_pattern = re.compile(
            r"\b(?:" + "|".join(re.escape(c.lower()) for c in cities) + r")\b"
        )

        # Street address recognizer
        street_recognizer = PatternRecognizer(
            supported_entity="US_STREET_ADDRESS",
            patterns=[
                Pattern("us_street_address", self.US_STREET_ADDRESS_PATTERN, 0.65),
                Pattern("us_street_misspelled", self._MISSPELLED_STREET_PATTERN, 0.5),
                Pattern("us_highway", self._HIGHWAY_PATTERN, 0.65),
                Pattern("us_state_zip", self._STATE_ZIP_PATTERN, 0.7),
            ],
            supported_language="en",
        )
        self._analyzer.registry.add_recognizer(street_recognizer)

        zip_recognizer = PatternRecognizer(
            supported_entity="US_ZIP_CODE",
            patterns=[
                Pattern("us_zip_plus_4", self.ZIP_PLUS_4_PATTERN, 0.7),
                Pattern("us_zip_5", self.ZIP_5_PATTERN, 0.4),
            ],
            supported_language="en",
        )
        self._analyzer.registry.add_recognizer(zip_recognizer)

        # Register name recognizers
        from pii_washer.name_recognizer import (
            CapitalizedPairRecognizer,
            DictionaryNameRecognizer,
            GreetingNameRecognizer,
            TitleNameRecognizer,
        )
        self._analyzer.registry.add_recognizer(TitleNameRecognizer())
        self._analyzer.registry.add_recognizer(DictionaryNameRecognizer())
        self._analyzer.registry.add_recognizer(CapitalizedPairRecognizer())
        self._analyzer.registry.add_recognizer(GreetingNameRecognizer())

        # SSN recognizer — remove Presidio's built-in to avoid false positives
        # from area codes like 9xx that Presidio doesn't validate.
        self._remove_builtin_recognizer("UsSsnRecognizer")
        self._analyzer.registry.add_recognizer(CustomSSNRecognizer())

        # Phone recognizer — remove Presidio's built-in PhoneRecognizer
        # to prevent no-separator 10-digit numbers from matching without context.
        self._remove_builtin_recognizer("PhoneRecognizer")
        self._analyzer.registry.add_recognizer(CustomPhoneRecognizer())

        # PO Box recognizer
        self._analyzer.registry.add_recognizer(POBoxRecognizer())

        # Credit card recognizer
        self._analyzer.registry.add_recognizer(CustomCreditCardRecognizer())

        # Enhanced IP recognizer
        self._analyzer.registry.add_recognizer(CustomIPRecognizer())

        # Obfuscated email recognizer
        self._analyzer.registry.add_recognizer(ObfuscatedEmailRecognizer())

        # Labeled identifier recognizer (routing/account/passport/plate/…)
        self._analyzer.registry.add_recognizer(LabeledIdentifierRecognizer())

    def _remove_builtin_recognizer(self, recognizer_name: str) -> None:
        """Remove a Presidio built-in recognizer by name from the registry."""
        registry = self._analyzer.registry
        registry.recognizers = [
            r for r in registry.recognizers if r.name != recognizer_name
        ]

    def detect(self, text: str, confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD, language: str = "en") -> list[dict]:
        if not isinstance(text, str) or not text:
            raise ValueError("Text cannot be empty")
        if not (0.0 <= confidence_threshold <= 1.0):
            raise ValueError("Confidence threshold must be between 0.0 and 1.0")

        results = self._analyzer.analyze(
            text=text,
            entities=list(self.ENTITY_MAPPING.keys()),
            language=language,
        )

        detections = []
        for result in results:
            category = self.ENTITY_MAPPING.get(result.entity_type)
            if category is None:
                continue

            start = result.start
            end = result.end
            confidence = result.score
            original_value = text[start:end]

            # NER name spans can bleed across a line break into the next
            # line's label ("Michael Torres\nDate of birth") — trim at the newline
            if category == "NAME" and "\n" in original_value:
                original_value = original_value.split("\n", 1)[0].rstrip()
                if not original_value:
                    continue
                end = start + len(original_value)

            # DOB — implausible date shapes are dropped entirely;
            # no context → surface at low confidence 0.2 instead of dropping
            if category == "DOB":
                if not self._plausible_dob(original_value):
                    continue
                if not self._has_dob_context(text, start):
                    confidence = 0.2

            if category == "URL" and not self._is_pii_url(original_value):
                continue

            if category == "ADDRESS" and result.entity_type == "US_ZIP_CODE":
                # ZIP+4 always passes (distinctive format)
                if "-" not in original_value:
                    # 5-digit zip: require address context
                    if not self._has_zip_context(text, start):
                        continue

            # Filter loopback and link-local IPs
            if category == "IP" and self._is_local_ip(original_value):
                continue

            if confidence < confidence_threshold:
                continue

            detections.append({
                "category": category,
                "original_value": original_value,
                "positions": [{"start": start, "end": end}],
                "confidence": confidence,
            })

        detections = self._deduplicate(detections)
        detections.sort(key=lambda d: d["positions"][0]["start"])

        for i, det in enumerate(detections, start=1):
            det["id"] = f"pii_{i:03d}"

        return detections

    @staticmethod
    def _plausible_dob(value: str) -> bool:
        """spaCy tags digit runs (card-number fragments) and relative words
        ("today") as DATE_TIME; neither is a plausible date of birth.
        Require at least one digit, and reject bare digit runs longer than
        a year (a real date has separators or month words)."""
        digit_count = sum(c.isdigit() for c in value)
        if digit_count == 0:
            return False
        if digit_count > 4 and re.fullmatch(r"[\d\s]+", value):
            return False
        return True

    def _has_dob_context(self, text: str, span_start: int) -> bool:
        window_start = max(0, span_start - self.DOB_CONTEXT_WINDOW)
        context = text[window_start:span_start].lower()
        return any(kw in context for kw in self.DOB_CONTEXT_KEYWORDS)

    def _has_zip_context(self, text: str, span_start: int) -> bool:
        """Check if address-related context appears before a 5-digit zip code."""
        window_start = max(0, span_start - self.ZIP_CONTEXT_WINDOW)
        context = text[window_start:span_start]

        # Check explicit ZIP keywords (case-insensitive)
        context_lower = context.lower()
        for kw in self.ZIP_CONTEXT_KEYWORDS:
            if kw in context_lower:
                return True

        # Check for state abbreviations (case-sensitive — they're uppercase)
        for abbr in self.US_STATE_ABBREVIATIONS:
            if re.search(r"(?:^|[\s,])" + abbr + r"(?:[\s,]|$)", context):
                return True

        # Check for street type suffixes (case-insensitive, whole word)
        for st_type in self.US_STREET_TYPES:
            if re.search(r"\b" + re.escape(st_type) + r"\.?\b", context, re.IGNORECASE):
                return True

        # Check for known city names (single pre-compiled regex)
        if self._us_cities_pattern.search(context_lower):
            return True

        return False

    def _is_pii_url(self, url: str) -> bool:
        url_lower = url.lower()
        # Check explicit patterns
        if any(pattern in url_lower for pattern in self.PII_URL_PATTERNS):
            return True
        # Profile path heuristic
        return self._is_profile_path_url(url_lower)

    def _is_profile_path_url(self, url_lower: str) -> bool:
        """Check for /@username, /user/name, /u/name, /profile/name, /~/name, /people/name."""
        profile_patterns = [
            r"/user/([^/\s?#]+)",
            r"/u/([^/\s?#]+)",
            r"/profile/([^/\s?#]+)",
            r"/~/([^/\s?#]+)",
            r"/people/([^/\s?#]+)",
            r"/@([^/\s?#]+)",
        ]
        for pat in profile_patterns:
            m = re.search(pat, url_lower)
            if m:
                segment = m.group(1)
                if segment not in self._PROFILE_PATH_EXCLUSIONS:
                    return True
        return False

    def _is_local_ip(self, ip: str) -> bool:
        """Return True for loopback/link-local addresses that shouldn't be flagged."""
        ip_lower = ip.lower()
        # IPv6 loopback ::1 and link-local fe80::
        if ip_lower == "::1" or ip_lower.startswith("fe80::"):
            return True
        # IPv4 loopback
        if ip_lower.startswith("127."):
            return True
        return False

    def _deduplicate(self, detections: list[dict]) -> list[dict]:
        if len(detections) <= 1:
            return detections

        to_remove = set()
        for i in range(len(detections)):
            if i in to_remove:
                continue
            for j in range(i + 1, len(detections)):
                if j in to_remove:
                    continue

                s_i = detections[i]["positions"][0]["start"]
                e_i = detections[i]["positions"][0]["end"]
                s_j = detections[j]["positions"][0]["start"]
                e_j = detections[j]["positions"][0]["end"]

                if s_i == s_j and e_i == e_j:
                    # Exact span match: keep higher confidence
                    if detections[i]["confidence"] >= detections[j]["confidence"]:
                        to_remove.add(j)
                    else:
                        to_remove.add(i)
                elif s_j >= s_i and e_j <= e_i:
                    # j is contained in i: keep i (longer)
                    to_remove.add(j)
                elif s_i >= s_j and e_i <= e_j:
                    # i is contained in j: keep j (longer)
                    to_remove.add(i)

        return [d for idx, d in enumerate(detections) if idx not in to_remove]
