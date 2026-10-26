import re
import unicodedata
from typing import List, Dict, Any, Optional

GUEST_ROSTER = [
    {
        "id": 1,
        "name": "لیلا",
        "aliases": ["leila", "leyla", "layla", "leili"],
        "car_group": 1,
        "is_driver": True
    },
    {
        "id": 2,
        "name": "امیر (Amir)",
        "aliases": ["amir", "amirali", "امير"],
        "car_group": 0,
        "is_driver": False
    },
    {
        "id": 3,
        "name": "مسعود (Masoud)",
        "aliases": ["masoud", "masood", "massoud", "masud"],
        "car_group": 0,
        "is_driver": False
    },
    {
        "id": 4,
        "name": "رویا (Roya)",
        "aliases": ["roya", "roia", "roya"],
        "car_group": 2,
        "is_driver": False
    },
    {
        "id": 5,
        "name": "یاسمین (Yasamin)",
        "aliases": ["yasamin", "yasmin", "yassamin", "یاسمن"],
        "car_group": 0,
        "is_driver": False
    },
    {
        "id": 6,
        "name": "احسان (Ehsan)",
        "aliases": ["ehsan", "ehssan", "ihsan"],
        "car_group": 2,
        "is_driver": False
    },
    {
        "id": 7,
        "name": "عارف (Aref)",
        "aliases": ["aref", "arif"],
        "car_group": 2,
        "is_driver": True
    },
    {
        "id": 8,
        "name": "نرگس (Narges)",
        "aliases": ["narges", "nargess", "nargis"],
        "car_group": 3,
        "is_driver": False
    },
    {
        "id": 9,
        "name": "سمیرا (Samira)",
        "aliases": ["samira", "sameera"],
        "car_group": 3,
        "is_driver": False
    },
    {
        "id": 10,
        "name": "سیاوش (Siavash)",
        "aliases": ["siavash", "siyavash", "siyawash", "siawash"],
        "car_group": 6,
        "is_driver": True
    },
    {
        "id": 11,
        "name": "محا (Moha)",
        "aliases": ["moha", "maha", "mohaa"],
        "car_group": 6,
        "is_driver": False
    },
    {
        "id": 12,
        "name": "مجتبی (Mojtaba)",
        "aliases": ["mojtaba", "mojtoba", "mojtabaa"],
        "car_group": 3,
        "is_driver": False
    },
    {
        "id": 13,
        "name": "مهدیه (Mahdieh)",
        "aliases": ["mahdieh", "mahdiyeh", "mahdie"],
        "car_group": 6,
        "is_driver": False
    },
    {
        "id": 14,
        "name": "فرهود (Farhood)",
        "aliases": ["farhood", "farhud", "farhoud"],
        "car_group": 5,
        "is_driver": True
    },
    {
        "id": 15,
        "name": "ارشک (Arashk)",
        "aliases": ["arashk", "arshak", "ارشك"],
        "car_group": 5,
        "is_driver": False
    },
    {
        "id": 16,
        "name": "نونا (Nona)",
        "aliases": ["nona", "noona"],
        "car_group": 5,
        "is_driver": False
    },
    {
        "id": 17,
        "name": "پرهام (Parham)",
        "aliases": ["parham", "prham"],
        "car_group": 6,
        "is_driver": False
    },
    {
        "id": 18,
        "name": "مهدی (Mehdi)",
        "aliases": ["mehdi", "mahdi", "مهدي"],
        "car_group": 0,
        "is_driver": False
    },
    {
        "id": 19,
        "name": "همراه خاطره",
        "aliases": [
            "hamrah khatereh", "hamrahe khatereh", "hamrah khatere",
            "khatereh hamrah", "دوست پسر خاطره", "پارتنر خاطره", "همراه خاطره"
        ],
        "car_group": 1,
        "is_driver": False
    },
    {
        "id": 20,
        "name": "خاطره",
        "aliases": ["khatereh", "khatere", "xatereh"],
        "car_group": 1,
        "is_driver": False
    },
    {
        "id": 21,
        "name": "بهنود (behnoud)",
        "aliases": ["behnoud", "behnood", "behnud"],
        "car_group": 4,
        "is_driver": False
    },
    {
        "id": 22,
        "name": "همراه لیلا",
        "aliases": [
            "hamrah leila", "hamrahe leila", "hamrah leyla",
            "leila hamrah", "دوست پسر لیلا", "پارتنر لیلا", "همراه لیلا"
        ],
        "car_group": 1,
        "is_driver": False
    },
    {
        "id": 23,
        "name": "روژان",
        "aliases": ["rozhan", "rojan", "rojhan"],
        "car_group": None,
        "is_driver": False
    },
    {
        "id": 24,
        "name": "سایه",
        "aliases": ["sayeh", "saye", "saayeh"],
        "car_group": None,
        "is_driver": False
    },
    {
        "id": 25,
        "name": "کیانا",
        "aliases": ["kiana", "kiyana"],
        "car_group": None,
        "is_driver": False
    },
    {
        "id": 26,
        "name": "الناز",
        "aliases": ["elnaz", "elnazz"],
        "car_group": None,
        "is_driver": False
    },
    {
        "id": 27,
        "name": "کیمیا",
        "aliases": ["kimia", "kimiya", "kimya"],
        "car_group": None,
        "is_driver": False
    },
    {
        "id": 28,
        "name": "یاسر",
        "aliases": ["yaser", "yasser"],
        "car_group": None,
        "is_driver": False
    },
    {
        "id": 29,
        "name": "پوریا",
        "aliases": ["pouria", "pooria", "poorya", "pourya"],
        "car_group": None,
        "is_driver": False
    },
    {
        "id": 30,
        "name": "یگانه",
        "aliases": ["yeganeh", "yegane"],
        "car_group": None,
        "is_driver": False
    },
    {
        "id": 31,
        "name": "علی",
        "aliases": ["ali", "aly"],
        "car_group": None,
        "is_driver": False
    },
    {
        "id": 32,
        "name": "محمدرضا",
        "aliases": ["mohammadreza", "mohamadreza", "mohammad reza", "محمد رضا"],
        "car_group": None,
        "is_driver": False
    },
    {
        "id": 33,
        "name": "علیرضا",
        "aliases": ["alireza", "ali reza", "علی رضا"],
        "car_group": None,
        "is_driver": False
    },
    {
        "id": 34,
        "name": "مصطفی",
        "aliases": ["mostafa", "mostafaa", "mostapha"],
        "car_group": None,
        "is_driver": False
    },
    {
        "id": 35,
        "name": "ابلفضل",
        "aliases": [
            "abolfazl", "abolfadl", "abolfazel", "abolfazell",
            "ابوالفضل", "ابولفضل", "ابلفضل"
        ],
        "car_group": None,
        "is_driver": False
    },
    {
        "id": 36,
        "name": "کسری",
        "aliases": ["kasra", "kasraa", "kasri", "کسرا"],
        "car_group": None,
        "is_driver": False
    },
    {
        "id": 37,
        "name": "پرنیان",
        "aliases": ["parnian", "parnyan", "parniyan"],
        "car_group": None,
        "is_driver": False
    },
    {
        "id": 38,
        "name": "ارین",
        "aliases": ["arian", "arin", "aarian", "آرین"],
        "car_group": None,
        "is_driver": False
    },
    {
        "id": 39,
        "name": "امیرعلی",
        "aliases": ["amirali", "amir ali", "امیر علی"],
        "car_group": None,
        "is_driver": False
    },
    {
        "id": 40,
        "name": "نازگل",
        "aliases": ["nazgol", "naazgol"],
        "car_group": None,
        "is_driver": False
    },
    {
        "id": 41,
        "name": "کایل",
        "aliases": ["kyle", "kayle", "kile"],
        "car_group": None,
        "is_driver": False
    },
    {
        "id": 42,
        "name": "امیربهادر",
        "aliases": ["amirbahador", "amir bahador", "امیر بهادر"],
        "car_group": None,
        "is_driver": False
    },
    {
        "id": 43,
        "name": "کیمیا (۲)",
        "aliases": ["kimia 2", "kimia۲", "kimiya 2", "کیمیا 2", "کیمیا ۲"],
        "car_group": None,
        "is_driver": False
    },
    {
        "id": 44,
        "name": "سوگل",
        "aliases": ["sogol", "soogol", "sogand"],
        "car_group": None,
        "is_driver": False
    },
    {
        "id": 45,
        "name": "مصطفی (۲)",
        "aliases": ["mostafa 2", "mostafa۲", "مصطفی 2", "مصطفی ۲"],
        "car_group": None,
        "is_driver": False
    },
    {
        "id": 46,
        "name": "هومن",
        "aliases": ["hooman", "houman", "homan"],
        "car_group": None,
        "is_driver": False
    },
    {
        "id": 47,
        "name": "ارزو",
        "aliases": ["arezoo", "arezu", "arzoo", "آرزو", "ارزو"],
        "car_group": None,
        "is_driver": False
    },
    {
        "id": 48,
        "name": "علی (۲)",
        "aliases": ["ali 2", "ali۲", "علی 2", "علی ۲"],
        "car_group": None,
        "is_driver": False
    },
    {
        "id": 49,
        "name": "بردیا",
        "aliases": ["bardia", "bardya", "bardiya"],
        "car_group": None,
        "is_driver": False
    },
    {
        "id": 50,
        "name": "بهناد",
        "aliases": ["behnad", "behnaad"],
        "car_group": None,
        "is_driver": False
    },
    {
        "id": 51,
        "name": "مینا",
        "aliases": ["mina", "meena"],
        "car_group": None,
        "is_driver": False
    },
    {
        "id": 52,
        "name": "فرید",
        "aliases": ["farid", "fareed"],
        "car_group": 4,
        "is_driver": False
    },
    {
        "id": 53,
        "name": "حامد",
        "aliases": ["hamed", "haamed"],
        "car_group": 0,
        "is_driver": False
    },
]

def normalize_text(text: str) -> str:
    """Normalizes Persian/Arabic characters and removes diacritics/parentheses."""
    if not text:
        return ""
    t = text.strip().lower()
    # Replace Arabic characters with standard Persian
    t = t.replace("ي", "ی").replace("ك", "ک").replace("ة", "ه").replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    t = t.replace("\u200c", " ")  # zero-width non-joiner
    t = re.sub(r"[^\w\s\(\)۲2]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

def levenshtein_distance(s1: str, s2: str) -> int:
    """Calculates Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]

def similarity_ratio(s1: str, s2: str) -> float:
    """Returns a float between 0.0 and 1.0 indicating string similarity."""
    s1, s2 = normalize_text(s1), normalize_text(s2)
    if not s1 or not s2:
        return 0.0
    if s1 == s2:
        return 1.0
    max_len = max(len(s1), len(s2))
    dist = levenshtein_distance(s1, s2)
    return 1.0 - (dist / max_len)

def find_matching_guests(query: str) -> List[Dict[str, Any]]:
    """
    Search guest list by normalized query, insensitive to:
    - English transliteration (e.g. 'hamed', 'leila', 'siavash', 'arezoo')
    - Persian script ('حامد', 'لیلا', 'سیاوش', 'آرزو')
    - Common misspellings and typos ('leyla', 'farhud', 'hamd', 'abolfazl')
    
    Returns list of matched guest dicts, sorted by confidence.
    """
    q_raw = query.strip().lower()
    q_norm = normalize_text(query)
    if not q_norm and not q_raw:
        return []

    # 1. Exact alias match or exact name match
    exact_matches = []
    for g in GUEST_ROSTER:
        # Check display name
        if q_norm == normalize_text(g["name"]):
            exact_matches.append(g)
            continue
        # Check base name without parentheses
        base = re.sub(r"\(.*?\)", "", g["name"]).strip()
        if q_norm == normalize_text(base):
            exact_matches.append(g)
            continue
        # Check aliases
        for alias in g.get("aliases", []):
            if q_raw == alias.lower() or q_norm == normalize_text(alias):
                if g not in exact_matches:
                    exact_matches.append(g)
                break

    if exact_matches:
        return exact_matches

    # 2. Substring matching in aliases or names
    substring_matches = []
    for g in GUEST_ROSTER:
        matched = False
        all_terms = [g["name"]] + g.get("aliases", [])
        for term in all_terms:
            t_norm = normalize_text(term)
            t_raw = term.lower()
            if (len(q_raw) >= 3 and q_raw in t_raw) or (len(q_norm) >= 3 and q_norm in t_norm):
                matched = True
                break
        if matched and g not in substring_matches:
            substring_matches.append(g)

    if substring_matches:
        return substring_matches

    # 3. Fuzzy Levenshtein matching on all terms and aliases (tolerates typos)
    fuzzy_matches = []
    for g in GUEST_ROSTER:
        best_sim = 0.0
        all_terms = [g["name"]] + g.get("aliases", [])
        for term in all_terms:
            # Check raw similarity (for English)
            sim_raw = similarity_ratio(q_raw, term.lower())
            # Check normalized similarity (for Persian)
            sim_norm = similarity_ratio(q_norm, normalize_text(term))
            best_sim = max(best_sim, sim_raw, sim_norm)

        # Threshold: if query is short (3-4 chars), require > 0.70; otherwise > 0.65
        threshold = 0.72 if len(q_raw) <= 4 else 0.65
        if best_sim >= threshold:
            fuzzy_matches.append((best_sim, g))

    if fuzzy_matches:
        fuzzy_matches.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in fuzzy_matches]

    # 4. Multi-word fallback: if user typed first + last name, try matching just the first name
    words_norm = q_norm.split()
    words_raw = q_raw.split()
    if len(words_norm) > 1 or len(words_raw) > 1:
        first_token = words_norm[0] if words_norm else words_raw[0]
        first_matches = find_matching_guests(first_token)
        if first_matches:
            return first_matches

    return []

def get_car_group_members(car_group: int) -> List[Dict[str, Any]]:
    """Retrieves all guests pre-assigned to a specific car group."""
    if car_group is None:
        return []
    return [g for g in GUEST_ROSTER if g.get("car_group") == car_group]
