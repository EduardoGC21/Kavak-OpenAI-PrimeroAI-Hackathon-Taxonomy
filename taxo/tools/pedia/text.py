"""Vendored from pedia-harness@3d980add check/ratchets/common.py (words, fold, SIZE_TOKEN, FILLER). Pure code; only imports adjusted. Do not edit by hand:
port fixes into taxo/tools/checks.py or re-vendor."""
import re
import unicodedata

FILLER = {"original", "classic", "assorted", "variety", "the", "and", "a", "in", "of", "with"}
SIZE_TOKEN = re.compile(r"^(\d+([.,]\d+)?(g|kg|oz|lb|lbs|ml|l|ct|pk|pack|count|fl)?|(19|20)\d0s)$")


def words(name: str | None) -> list[str]:
    """NFKD ascii, lower, & = and, apostrophes dropped, [a-z0-9]+ runs, a final s folded off (not ss): the fold the
    census twins and Harry's 'spelling / plural' rule (food.cnv.11) both use."""
    s = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode().lower().replace("&", " and ")
    s = s.replace("'", "")
    return [re.sub(r"(?<=[a-z]{2}[a-rt-z])s$", "", w) for w in re.findall(r"[a-z0-9]+", s)]


def fold(name: str | None) -> str:
    return " ".join(words(name))


def sorted_key(name: str | None) -> tuple:
    return tuple(sorted(words(name)))

