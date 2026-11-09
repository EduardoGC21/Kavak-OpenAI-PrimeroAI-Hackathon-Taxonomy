"""Vendored from pedia-harness@3d980add pipeline/compile/food/brandpass_tools/card_check.py (card vocabularies + fold/toks/stem/has_phrase/has_tokens). Pure code; only imports adjusted. Do not edit by hand:
port fixes into taxo/tools/checks.py or re-vendor."""
import re
import unicodedata

SPECIAL = {"brand_only", "bundle", "not_food", "other_brand"}
STOP = {"and", "with", "of", "the", "a", "an", "in", "for", "de", "y", "n", "s", "by", "en", "la", "el", "le", "du", "di"}
TYPE = set("""candy candies chips chip crisps snack snacks chocolate chocolates gummies gummy gummi drink drinks beverage
beverages soda tea teas coffee juice cookies cookie biscuits biscuit crackers cracker sauce sauces seasoning seasonings
spice spices syrup syrups mix mixes powder bar bars bites food foods product products treat treats confectionery
confection sweets water energy flavored flavoured flavor flavour flavors flavours assorted variety""".split())
CLAIM = set("""organic natural vegan keto gluten free nongmo gmo non kosher halal sugar zero diet lite light reduced fat
low sodium calorie calories protein whole grain unsweetened sugarfree""".split())
SIZE = set("""fun size king share bulk value pack packs count ct pc pcs piece pieces oz ml l g kg lb lbs fl pk box bag
case jar can cans bottle bottles tub pouch""".split())
SEASON = set("""halloween christmas easter valentine valentines holiday holidays spring summer fall autumn winter seasonal
edition limited ramadan diwali xmas""".split())
TIER_WORDS = ["zero", "sugar free", "diet", "decaf", "caffeine free", "reduced fat", "light", "lite", "no sugar added",
              "unsweetened", "keto"]
FORMAT_WORDS = ["pods", "k cup", "kcup", "ground", "whole bean", "instant", "powder", "concentrate", "ready to drink", "bites",
                "minis", "mini", "giant", "sticks", "singles", "liquid", "drops", "syrup", "bar", "bars", "gummies", "hard candy",
                "lollipop", "lollipops", "pops", "chews", "dispenser", "refills", "spray", "grinder", "capsules", "tablets"]
CATCHALL = set("""candy candies chocolate chocolates product products sweets snack snacks food foods treat treats
confectionery confections goods items other misc miscellaneous more""".split())
MARKET = set("""uk us usa japan japanese mexico mexican canada canadian europe european eu import imported international
global asia asian korea korean china chinese germany german""".split())
FLAVOUR = set("""red blue green yellow orange purple pink black white gold rainbow cherry strawberry raspberry grape lemon
lime apple watermelon mango peach pineapple tropical berry berries banana vanilla mint coconut caramel cola citrus fruit
fruity original assorted wholesale theater theatre bulk mixed sour""".split())
OPTIONAL = {"original", "classic", "regular", "signature"}   # the flagship's name word; titles often omit it
PACKCH = {"assorted", "wholesale", "theater", "theatre", "bulk", "mixed", "variety", "pack", "packs", "multipack", "gift"}
DESCRIPTOR = set("""soft chewy crunchy crispy creamy smooth delicious premium gourmet fresh tasty""".split())
MIX_WORDS = ("variety", "assorted", "assortment", "mixed", "sampler", "medley")   # not bare "mix": Drink Mix, Cake Mix
ASSORT_NAMES = {"assortment", "assorted", "variety", "variety pack", "variety packs", "mixed", "assortments"}


def fold(s) -> str:
    """Latin accents dropped, case folded, other scripts (Japanese, Korean ...) kept: NFKD, drop combining marks, NFKC."""
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = unicodedata.normalize("NFKC", "".join(ch for ch in s if unicodedata.category(ch) != "Mn")).casefold()
    s = re.sub(r"['\u2019`]", "", s)
    return " ".join(re.findall(r"[^\W_]+", s))


def toks(s) -> list[str]:
    return fold(s).split()


def stem(t: str) -> str:
    return t[:-1] if len(t) > 3 and t.endswith("s") and not t.endswith("ss") else t


def has_phrase(title_f: str, phrase_f: str) -> bool:
    if not phrase_f:
        return False
    return re.search(r"(?<![a-z0-9])" + re.escape(phrase_f) + r"(?![a-z0-9])", title_f) is not None


def has_tokens(title_tokens: set, need: list[str]) -> bool:
    """A Latin word must be a title word (plural-tolerant); a word in another script is matched inside a title word
    (Japanese titles carry no spaces)."""
    return all((stem(t) in title_tokens) if t.isascii() else any(t in x for x in title_tokens) for t in need)


