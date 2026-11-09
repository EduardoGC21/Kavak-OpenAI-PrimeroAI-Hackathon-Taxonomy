"""Vendored from pedia-harness@3d980add packages/engine/pedia_engine/legacy/lib2.py (fragrance CONC / FORMS / EDITION_WORDS / AUDIENCE). Pure code; only imports adjusted. Do not edit by hand:
port fixes into taxo/tools/checks.py or re-vendor."""
CONC = [("extrait de parfum", "Extrait de Parfum"), ("extrait", "Extrait de Parfum"), ("eau de parfum", "EDP"),
        ("edp", "EDP"), ("eau de toilette", "EDT"), ("edt", "EDT"), ("eau de cologne", "EDC"), ("edc", "EDC"),
        ("parfum", "Parfum"), ("cologne", "Cologne")]
FORMS = [("body mist", "body mist"), ("hair mist", "hair mist"), ("body spray", "body spray"),
         ("concentrated perfume oil", "oil"), ("perfume oil", "oil"), ("concentrated oil", "oil"),
         ("deodorant", "deodorant"), ("body lotion", "body lotion"), ("shower gel", "shower gel"),
         ("after shave", "aftershave"), ("aftershave", "aftershave")]
EDITION_WORDS = ["limited edition", "collector s edition", "collectors edition", "special edition", "holiday edition",
                 "christmas", "halloween", "easter", "valentine", "valentines", "seasonal", "new edition"]
AUDIENCE = [("for men", "men"), ("for women", "women"), ("pour homme", "men"), ("pour femme", "women"),
            ("unisex", "unisex"), ("for him", "men"), ("for her", "women")]
AGREE_TOL = 0.06  # pedia_engine/supply/units.py: two statements of one quantity
