"""Agents (OpenAI Agents SDK). The same roles serve every domain; a domain only supplies its pack and data.

placer    listing -> node, with taxonomy tools                 (LLM)
judge     placement -> accept / reject / abstain, fast then strong (LLM)
proposer  disagreement cluster -> candidate rule               (LLM)
curator   admit / promote / retire rules on their record        (code: agents never read labels)
"""
