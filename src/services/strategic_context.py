"""Strategic context search functionality for Pinecone Assistant."""

import logging
import re
from typing import Dict, Any, List
from pathlib import Path
import yaml

try:
    from ..api.assistant_client import PineconeAssistantClient
    from ..models.models import StrategyContextParams, ContextSearchResult, StrategyContextResult, AssistantContextParams
    from ..util.secure_logging import setup_secure_logging
    from ..util.text_utils import extract_key_terms
except ImportError:
    from api.assistant_client import PineconeAssistantClient
    from models.models import StrategyContextParams, ContextSearchResult, StrategyContextResult, AssistantContextParams
    from util.secure_logging import setup_secure_logging
    from util.text_utils import extract_key_terms

# SECURITY FIX (L-1): Use secure logging with auto-redaction
logger = setup_secure_logging(__name__, level=logging.INFO)


class StrategicContextSearcher:
    """Executes strategic context searches using YAML patterns."""
    
    def __init__(self, client: PineconeAssistantClient, config_path: str = None):
        """Initialize with client and configuration path."""
        self.client = client

        # If no path provided, use absolute path to project root
        if config_path is None:
            # Now in src/services/, so need to go up 2 levels to reach project root
            config_path = str(Path(__file__).parent.parent.parent / "strategic-searches.yaml")

        self.config_path = config_path
        self._patterns = None
    
    def _load_patterns(self) -> Dict[str, Any]:
        """Load search patterns from YAML configuration."""
        if self._patterns is None:
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self._patterns = yaml.safe_load(f)
                logger.info(f"Loaded strategic search patterns from {self.config_path}")
            except Exception as e:
                logger.error(f"Failed to load strategic search patterns: {e}")
                self._patterns = {}
        return self._patterns
    
    def _substitute_template(self, template: str, primary: str, key_terms: List[str]) -> str:
        """Substitute template variables with actual values."""
        # Replace primary placeholder
        query = template.replace("{primary}", primary)
        
        # Replace key terms placeholder
        key_terms_str = " ".join(key_terms)
        query = query.replace("{key_terms}", key_terms_str)
        
        return query.strip()
    
    def execute_strategic_context_search(self, params: StrategyContextParams) -> Dict[str, Any]:
        """Execute strategic context search using YAML patterns."""
        logger.info(f"Starting strategic context search for query: '{params.query}' in domain: '{params.domain}'")
        
        # Load search patterns
        patterns = self._load_patterns()
        
        # Get domain patterns
        if params.domain not in patterns:
            available_domains = list(patterns.keys())
            raise ValueError(f"Domain '{params.domain}' not found. Available domains: {available_domains}")
        
        domain_config = patterns[params.domain]
        search_patterns = domain_config.get("searches", [])
        
        if not search_patterns:
            raise ValueError(f"No search patterns found for domain '{params.domain}'")

        # Extract key terms for template substitution
        key_terms = extract_key_terms(params.query, max_terms=5)
        
        # Execute searches
        results = []
        searches_executed = []
        total_snippets = 0
        unique_sources = set()
        
        # Limit number of searches if specified
        max_searches = params.max_searches or len(search_patterns)
        search_patterns = search_patterns[:max_searches]
        
        for pattern in search_patterns:
            if not pattern.get("enabled", True):
                logger.debug(f"Skipping disabled pattern: {pattern.get('name', 'unnamed')}")
                continue
            
            pattern_name = pattern.get("name", "unnamed")
            query_template = pattern.get("query", "")
            
            if not query_template:
                logger.warning(f"Empty query template for pattern '{pattern_name}'")
                continue
            
            # Substitute template variables
            search_query = self._substitute_template(query_template, params.query, key_terms)
            
            logger.info(f"Executing context search '{pattern_name}': {search_query}")
            
            try:
                # Create context parameters for this search
                context_params = AssistantContextParams(
                    query=search_query,
                    top_k=params.top_k,
                    snippet_size=params.snippet_size
                )
                
                # Execute context search
                response = self.client.context(context_params)
                
                # Extract snippets
                snippets = response.get("snippets", [])
                snippet_count = len(snippets)
                
                # Track unique sources
                for snippet in snippets:
                    if isinstance(snippet, dict):
                        reference = snippet.get("reference", {})
                        if isinstance(reference, dict):
                            source_id = reference.get("id") or reference.get("file_id") or reference.get("url")
                            if source_id:
                                unique_sources.add(source_id)
                
                # Create result for this search
                search_result = ContextSearchResult(
                    pattern_name=pattern_name,
                    query_executed=search_query,
                    snippets=snippets,
                    snippet_count=snippet_count
                )
                
                results.append(search_result.model_dump())
                searches_executed.append(pattern_name)
                total_snippets += snippet_count
                
                logger.info(f"Search '{pattern_name}' completed: {snippet_count} snippets")
                
            except Exception as e:
                logger.error(f"Search '{pattern_name}' failed: {e}")
                # Continue with other searches
                continue
        
        # Create final result
        strategy_result = StrategyContextResult(
            query=params.query,
            domain=params.domain,
            searches_executed=searches_executed,
            results=results,
            total_snippets=total_snippets,
            unique_sources=len(unique_sources)
        )
        
        logger.info(f"Strategic context search completed: {len(searches_executed)} searches, {total_snippets} total snippets, {len(unique_sources)} unique sources")
        
        return strategy_result.model_dump()