from extraction.base import ClaimExtractor, ExtractedClaim
from extraction.heuristic import HeuristicClaimExtractor

__all__ = ["ClaimExtractor", "ExtractedClaim", "HeuristicClaimExtractor"]

# LLMClaimExtractor는 optional dependency(anthropic)를 필요로 하므로
# 지연 임포트로 노출한다: from extraction.llm import LLMClaimExtractor
