"""Vendored from pedia-harness@3d980add pipeline/compile/food/cleanpass_tools/attrs_pass.py (title size/count parser: find_sizes, find_counts). Pure code; only imports adjusted. Do not edit by hand:
port fixes into taxo/tools/checks.py or re-vendor."""
import re
import re



# ------------------------------------------------------------------------------------------------ title parser
G_PER = {"oz": 28.349523125, "lb": 453.59237, "kg": 1000.0, "g": 1.0}
ML_PER = {"fl oz": 29.5735295625, "ml": 1.0, "cl": 10.0, "l": 1000.0, "gal": 3785.411784, "quart": 946.352946,
          "pint": 473.176473}
UNIT_RX = (r"fl\.?\s*oz\.?|fl\.?\s*ounces?|fluid\s+ounces?|fz|ounces?|onzas?|oz|lbs?|pounds?|kgs?|kilograms?|kilos?|"
           r"grams?|gramm?e?s?|grs?|gm?s?|g|millilit(?:er|re)s?|ml|cl|lit(?:er|re)s?|ltrs?|lt|l|gallons?|gal|quarts?|qts?|"
           r"pints?")
UNIT_LA = UNIT_RX.replace("|lt|l|", "|lt|")      # after a count: " l" is a separator ("Pack of 50 l Include")
UNIT_CANON = {"floz": "fl oz","fz": "fl oz","flounce": "fl oz", "flounces": "fl oz", "fluidounce": "fl oz", "fluidounces": "fl oz",
              "ounce": "oz", "ounces": "oz", "onza": "oz", "onzas": "oz", "oz": "oz", "lb": "lb", "lbs": "lb",
              "pound": "lb", "pounds": "lb", "kg": "kg", "kgs": "kg", "kilogram": "kg", "kilograms": "kg", "kilo": "kg",
              "kilos": "kg", "gram": "g", "grams": "g", "gramm": "g", "gramme": "g", "grammes": "g", "gr": "g", "grs": "g",
              "g": "g", "gm": "g", "gms": "g", "gs": "g", "ml": "ml", "milliliter": "ml", "milliliters": "ml",
              "millilitre": "ml", "millilitres": "ml", "cl": "cl", "liter": "l", "liters": "l", "litre": "l",
              "litres": "l", "ltr": "l", "ltrs": "l", "lt": "l", "l": "l", "gal": "gal", "gallon": "gal",
              "gallons": "gal", "quart": "quart", "quarts": "quart", "qt": "quart", "qts": "quart", "pint": "pint",
              "pints": "pint"}
NUMX = r"\d+(?:\s+|\s*-\s*)\d\s*/\s*\d+|\d+\s*/\s*\d+|\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:[.,]\d+)?|\.\d+"
SIZE_RX = re.compile(r"(?<![A-WYZa-wyz0-9.,])(?<!\d/)(?<!\d\s/)(" + NUMX + r")\s*-?\s*(" + UNIT_RX + r")(?![a-z0-9])", re.I)
# a decimal size glued to the word before it ("Tea1.76oz", "Fun Size10.65oz", "Glass Jar.88 Ounce")
SIZE_GLUED = re.compile(r"(?<=[A-Za-z])(\d+\.\d+|\.\d+)\s*-?\s*(" + UNIT_RX + r")(?![a-z0-9])", re.I)
# a size that is a nutrient, not the net quantity: "20g Protein", "0g Sugar", "180mg", "5g of fiber", "per serving"
NUTRIENT_AFTER = re.compile(r"^\s*(?:of\s+)?(?:(?:net|added|total|plant[- ]based|whey|complete|vegan|dairy|grass[- ]fed|"
                            r"high[- ]quality|high|ultra|real|clean|pure|natural|organic|plant)\s+){0,3}(?:protein|sugars?|carbs?|carbohydrates?|fib(?:er|re)s?|fats?|"
                            r"caffeine|calories|sodium|collagen|prebiotic|probiotic|electrolytes?)\b", re.I)
NUTRIENT_BEFORE = re.compile(r"(?:\bper\s+serving|\bserving\s+size|\bprotein|\bsugars?|\bfib(?:er|re)|\bcaffeine|"
                             r"\bsodium|\bcarbs?)\s*[:\-]?\s*$", re.I)
YIELD_BEFORE = re.compile(r"\b(?:makes?|yields?|brews?|serves|up\s+to)\s+(?:about\s+|approx\.?\s+|up\s+to\s+)?$", re.I)
EACH_AFTER = re.compile(r"^\s*[\)\]]?\s*(?:each|ea\b|per\s+(?:bag|bar|can|bottle|pack|pouch|box|piece|unit|stick|packet|"
                        r"cup|serving|jar|tin|carton|tub)|individual(?:ly)?|bags?\s+each)", re.I)
EACH_BEFORE = re.compile(r"(?:\beach|\bper\s+(?:bag|bar|can|bottle|pack|pouch|box|piece|unit))\s*[:\-]?\s*\(?\s*$", re.I)
TOTAL_AFTER = re.compile(r"^\s*[\)\]]?\s*(?:total|in\s+total|net\s+wt|combined)\b", re.I)
TOTAL_BEFORE = re.compile(r"(?:\btotal(?:\s+(?:net\s+)?(?:weight|wt))?|\bnet\s+wt\.?|\bnet\s+weight|\bcombined|"
                          r"\bin\s+total)\s*[:\-]?\s*\(?\s*$", re.I)

# count words. CONTAINER: the size is per container (size x units). ITEM: small items in a bag / box (the size may be
# the bag's). OUTER: packs of sellable units (always size x n).
CONTAINER = (r"cans?|bottles?|bags?|boxes|box|pouch(?:es)?|jars?|tins?|tubs?|cartons?|bolsas?|"
             r"containers?|canisters?|cups?(?![\s-]*(?:of\s+)?(?:tea|coffee))|bricks?|bundles|snack\s+packs?|"
             r"share\s+packs?|bags?\s+of\s+chips")
ITEM = (r"count|ct|cnt|ea|pieces?|pcs?|pc|bars?|pods?|k[\s-]?cups?|capsules?|sticks?|tea\s*bags?|teabags?|packets?|"
        r"sachets?|candies|"
        r"cookies|lollipops?|lollies|pops|biscuits|wafers|eggs|truffles|rolls|tubes|units?|servings?\s+packets?|"
        r"individually\s+wrapped(?:\s+pieces)?|unidades|piezas|pezzi|stuks?|st[üu]ck")
OUTER = r"packs?|pk|pks|pkg|multipacks?"
COUNT_WORD_RX = re.compile(r"(?<![\w.,/])(\d{1,5})\s*[-]?\s*(?:(" + OUTER + r")|(" + CONTAINER + r")|(" + ITEM + r"))"
                           r"(?![a-z])\.?", re.I)
OF_RX = re.compile(r"\b(pack|case|lot|set|bundle|carton|tray|crate|multipack|box|bag|tub|jar|tin|bucket|pouch)\s+of\s+"
                   r"(\d{1,5})(?!\d|[.,]\d|\s*-?\s*(?:" + UNIT_LA + r")(?![a-z]))", re.I)
X_BEFORE_SIZE = re.compile(r"(?<![\w.,/])(\d{1,4})\s*[x×*]\s*$", re.I)                  # "12 x 330ml", "3x 1oz"
X_AFTER_SIZE = re.compile(r"^\s*[\)\]]?\s*[x×*]\s*(\d{1,4})(?!\d|[.,]\d|\s*-?\s*(?:" + UNIT_LA + r")(?![a-z]))", re.I)
N_BEFORE_SIZE = re.compile(r"(?<![\w.,/$])(\d{1,4})\s*(?:-|–)?\s*$")                    # "5 .625 oz bags", "12 - 1 oz bags"
WORD_AFTER_SIZE = re.compile(r"^\s*\.?\s*(?:[a-z]+\s+){0,2}?(" + CONTAINER + r"|" + ITEM + r"|packs)(?![a-z])", re.I)
TOTAL_COUNT = re.compile(r"(?<![\w.,/])(\d{1,5})\s+total\b(?:\s+(?:" + CONTAINER + r"|" + ITEM + r")(?![a-z]))?"
                         r"(?!\s*[a-z])|\btotal\s*(?:of\s*)?:?\s*(\d{1,5})(?!\d|[.,]\d)(?!\s*-?\s*(?:"
                         + UNIT_LA + r")(?![a-z]))|(?<![\w.,/])(\d{1,5})\s+(?:[a-z-]+\s+){0,2}?(?:" + CONTAINER + r"|"
                         + ITEM + r")\s+total\b", re.I)
MULTIPACK_WORD = re.compile(r"\bmulti[\s-]?packs?\b", re.I)
# "6 Boxes of 18 Tea Bags", "4 Bags of 25": outer containers x inner count
N_OF_M = re.compile(r"(?<![\w.,/])(\d{1,4})\s*[-]?\s*(?:boxes|bags|packs|cartons|cases|packages|tins|jars|pouches|tubs)\s+of\s+"
                    r"(\d{1,5})(?!\d|[.,]\d|\s*-?\s*(?:" + UNIT_LA + r")(?![a-z]))", re.I)
# a count with one or two words before its word ("60 Soursop Tea Bags"); used only when no other count is stated
GAP_COUNT = re.compile(r"(?<![\w.,/$#])(\d{1,4})\s+((?:[a-z][a-z'’-]*\s+){1,2}?)(tea\s*bags?|k[\s-]?cups?|pods|bars|"
                       r"sticks|packets|sachets|bags|cans|bottles|pouches|pieces|pcs|candies|lollipops|cookies|capsules|"
                       r"boxes|jars|packs|cups)(?![a-z])", re.I)
GAP_STOP = {"flavor", "flavors", "flavour", "flavours", "variety", "assorted", "layer", "bean", "beans", "grain", "grains",
            "cheese", "spice", "hour", "musketeers", "musketeer", "grand", "up", "in", "of", "x", "and", "or", "with",
            "per", "ounce", "oz", "lb", "pound", "gram", "gum", "minute", "minutes", "day", "days", "year", "years",
            "inch", "inches", "calorie", "calories", "percent", "star", "stars", "pepper", "peppers", "seed", "seeds"}
# counts that are not items: "Makes 35-50 Cups", "Serves 12", a range end
NOT_ITEMS_BEFORE = re.compile(r"(?:\bmakes|\bbrews|\byields|\bserves|\bup\s+to|\bfor)\s+(?:about\s+|approx\.?\s+)?"
                              r"(?:\d+\s*[-–]\s*)?$|\d\s*[-–]\s*$|\bto\s+$", re.I)


def _num(s: str) -> float | None:
    s = s.strip()
    mixed = re.fullmatch(r"(\d+)(?:\s+|\s*-\s*)(\d)\s*/\s*(\d+)", s)      # "1 1/2", "9-3/4"
    if mixed:
        w, a, b = (float(x) for x in mixed.groups())
        return w + a / b if b and a < b else None
    if "/" in s:
        a, b = [x.strip() for x in s.split("/", 1)]
        try:
            return float(a) / float(b) if float(b) else None
        except ValueError:
            return None
    if re.fullmatch(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?", s):
        s = s.replace(",", "")
    else:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def canon_unit(u: str) -> str | None:
    k = re.sub(r"[\s.]+", "", u.lower())
    return UNIT_CANON.get(k)


def fmt_num(x: float) -> str:
    return f"{round(x, 3):g}"


def norm_size(v: float, unit: str):
    """(value in g or ml, 'g' | 'ml')."""
    if unit in G_PER:
        return v * G_PER[unit], "g"
    if unit in ML_PER:
        return v * ML_PER[unit], "ml"
    return None, None


def find_sizes(t: str, dropped: list | None = None) -> list[dict]:
    """Net-quantity sizes stated in t; `dropped` (optional) collects the values (g) of nutrient sizes skipped."""
    out = []
    ms = []
    for m in SIZE_RX.finditer(t):
        ms.append((m.start(), m.end(), m.group(1), m.group(2), m.group(0)))
    for m in SIZE_GLUED.finditer(t):                     # "Tea1.76oz", "Original14.0oz", "Jar.88 Ounce"
        if not any(m.start() < e and s < m.end() for s, e, *_ in ms):
            ms.append((m.start(), m.end(), m.group(1), m.group(2), m.group(0)))
    for st_, en_, num_s, unit_s, text_ in sorted(ms):
        unit = canon_unit(unit_s)
        if unit in ("oz", "lb", "fl oz") and re.fullmatch(r"\d+,\d{1,2}", num_s.strip()):
            # "(Pack of 1,22 oz)": a comma is never a decimal before a US unit -> the size is the number after it
            num_s = num_s.split(",", 1)[1]
            st_ = en_ - len(text_) + text_.index(",") + 1
            text_ = t[st_:en_]
        v = _num(num_s)
        if unit is None or v is None or v <= 0:
            continue
        raw_u = unit_s.strip()
        gap = text_[len(num_s):].startswith((" ", "-")) if text_.startswith(num_s) else False
        # 'gs' only when glued ("120gs"); a bare lower-case 'l' only when glued ("1l") - "Pack of 50 l Include" is
        # a separator, "1.5 L" / "2l" are litres
        if raw_u.lower() == "gs" and gap:
            continue
        if raw_u == "l" and gap:
            continue
        m_start, m_end = st_, en_
        after, before = t[m_end:m_end + 40], t[max(0, m_start - 30):m_start]
        # nutrients are stated in grams and small ("20g Protein", "Protein: 5g"); "Sugar 1 Kg" is a size
        if unit == "g" and v <= 60 and (NUTRIENT_AFTER.match(after) or NUTRIENT_BEFORE.search(before)):
            if dropped is not None:
                dropped.append(v)
            continue
        if YIELD_BEFORE.search(before):                  # "Makes 10 Quarts", "Each Tea Bag Yields 1/2 Gallon"
            continue
        val, nu = norm_size(v, unit)
        if val is None or val > 200000:          # > 200 kg / 200 l: a typo or a non-size
            continue
        basis = None
        if EACH_AFTER.match(after) or EACH_BEFORE.search(before):
            basis = "item"
        elif TOTAL_AFTER.match(after) or TOTAL_BEFORE.search(before):
            basis = "pack"
        out.append({"start": m_start, "end": m_end, "v": v, "unit": unit, "val": val, "nu": nu, "basis": basis,
                    "text": text_})
    return out


def _overlaps(a, b, spans) -> bool:
    return any(a < e and s < b for s, e in spans)


def find_counts(t: str, sizes: list[dict]) -> dict:
    """outer packs, inner counts (with their word kind), a stated total, multipack word."""
    sz = [(s["start"], s["end"]) for s in sizes]
    used = []
    outer, inner, total, nofm = [], [], [], []
    for m in TOTAL_COUNT.finditer(t):
        n = next(int(g) for g in m.groups() if g)
        if 1 <= n <= 20000 and not _overlaps(m.start(), m.end(), sz):
            total.append((m.start(), n))
            used.append((m.start(), m.end()))
    for m in N_OF_M.finditer(t):
        a_, b_ = int(m.group(1)), int(m.group(2))
        if 1 <= a_ <= 1000 and 1 <= b_ <= 5000 and not _overlaps(m.start(), m.end(), sz + used):
            nofm.append((m.start(), a_, b_))
            used.append((m.start(), m.end()))
    for m in OF_RX.finditer(t):
        n = int(m.group(2))
        w = m.group(1).lower()
        if not (1 <= n <= 20000) or _overlaps(m.start(), m.end(), sz + used):
            continue
        if w in ("pack", "case", "lot", "set", "bundle", "carton", "tray", "crate", "multipack"):
            outer.append((m.start(), n, w))
        else:
            inner.append((m.start(), n, "item"))
        used.append((m.start(), m.end()))
    for m in COUNT_WORD_RX.finditer(t):
        n = int(m.group(1))
        if not (1 <= n <= 20000) or _overlaps(m.start(), m.end(), sz + used):
            continue
        # "4-Layer", "3 Musketeers" never reach here (no count word); "2024 Halloween" neither
        before = t[max(0, m.start() - 30):m.start()]
        if re.search(r"(?:\$|£|€|#|no\.?\s*|model\s*|size\s*|ages?\s*|for\s+)$", before, re.I) or \
                NOT_ITEMS_BEFORE.search(before):
            continue
        if re.match(r"\d+\s*-?\s*cups?\b", m.group(0), re.I) and any(s["unit"] in ("gal", "quart", "pint") for s in sizes):
            continue                                     # "(1/2 Gal. 8 Cups)": a volume, not 8 cups
        if m.group(2):
            outer.append((m.start(), n, m.group(2).lower()))
        elif m.group(3):
            inner.append((m.start(), n, "container"))
        else:
            inner.append((m.start(), n, "item"))
        used.append((m.start(), m.end()))
    # counts stated around a size: "12 x 330ml" / "330ml x 12" (outer), "5 .625 oz bags" (inner container)
    for s in sizes:
        pre, post = t[:s["start"]], t[s["end"]:]
        # "6 X 3.5 OZ", "4.4oz X 24 Count": the size of one of N (item basis), also when "24 Count" was read already
        mx = X_BEFORE_SIZE.search(pre)
        if mx:
            if not _overlaps(mx.start(1), mx.end(1), used):
                outer.append((mx.start(1), int(mx.group(1)), "x"))
                used.append((mx.start(1), mx.end(1)))
            s["basis"] = s["basis"] or "item"
            continue
        ma = X_AFTER_SIZE.match(post)
        if ma:
            a0 = s["end"] + ma.start(1)
            if not _overlaps(a0, a0 + len(ma.group(1)), used):
                outer.append((a0, int(ma.group(1)), "x"))
                used.append((a0, a0 + len(ma.group(1))))
            s["basis"] = s["basis"] or "item"
            continue
        # "10ct (3.0 oz)": a size in brackets right after a count is the whole count's
        if re.search(r"\b\d{1,5}\s*-?\s*(?:" + ITEM + r")\.?\s*[\(\[]\s*$", pre, re.I):
            s["basis"] = s["basis"] or "pack"
        mw = WORD_AFTER_SIZE.match(post)
        if mw:
            s["cword"] = mw.group(1)                     # "12oz can", "16 oz bottle": read by is_liquid_oz
        mn = N_BEFORE_SIZE.search(pre)
        if mw and mn and not _overlaps(mn.start(1), mn.end(1), used + sz):
            kind = "container" if re.fullmatch(CONTAINER, mw.group(1), re.I) else "item"
            inner.append((mn.start(1), int(mn.group(1)), kind))
            used.append((mn.start(1), mn.end(1)))
            s["basis"] = s["basis"] or "item"
        elif mw and (re.fullmatch(CONTAINER, mw.group(1), re.I) or re.fullmatch(r"packs|tubes|rolls", mw.group(1), re.I)):
            # "3.3 Ounce Bags", "0.5oz Snack Packs", "5-Ounce Bags": several containers of that size (item basis);
            # "12oz Can", "17.04oz Box": one container, whose contents a count may describe
            if re.search(r"(?:s|es)$", mw.group(1), re.I) and not re.fullmatch(r"(?:bag|box|can|jar|tin|tub)", mw.group(1), re.I):
                if s["basis"] is None:
                    s["basis"], s["glue"] = "item", True
            s["container"] = True
    if not nofm and all(x[1] == 1 for x in outer + inner + total):
        # nothing, or only "1 Count": "1 Count (80 Single Serve Cups)" -> the 80
        for m in GAP_COUNT.finditer(t):
            n = int(m.group(1))
            gap = [w.lower().strip("'’-") for w in m.group(2).split()]
            if not (2 <= n <= 5000) or 1900 <= n <= 2099 or any(w in GAP_STOP for w in gap):
                continue
            if _overlaps(m.start(), m.end(), sz) or NOT_ITEMS_BEFORE.search(t[max(0, m.start() - 30):m.start()]):
                continue
            w = m.group(3).lower()
            kind = "outer" if w == "packs" else ("container" if re.fullmatch(CONTAINER, w, re.I) else "item")
            (outer if kind == "outer" else inner).append((m.start(), n, "gap " + w) if kind == "outer" else (m.start(), n, kind))
            break
    return {"outer": sorted(outer), "inner": sorted(inner), "total": sorted(total), "nofm": sorted(nofm),
            "multipack_word": bool(MULTIPACK_WORD.search(t))}
