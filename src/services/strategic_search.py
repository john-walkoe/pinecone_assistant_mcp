"""Strategic search pattern processing for USPTO Pinecone Assistant MCP."""

import re
import yaml
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
try:
    from ..models.models import SearchPattern, SearchDomain, StrategySearchParams, AssistantChatParams, Message
    from ..api.assistant_client import PineconeAssistantClient
    from ..util.secure_logging import setup_secure_logging
    from ..util.text_utils import extract_key_terms
except ImportError:
    from models.models import SearchPattern, SearchDomain, StrategySearchParams, AssistantChatParams, Message
    from api.assistant_client import PineconeAssistantClient
    from util.secure_logging import setup_secure_logging
    from util.text_utils import extract_key_terms


# SECURITY FIX (L-1): Use secure logging with auto-redaction
logger = setup_secure_logging(__name__, level=logging.INFO)


class StrategySearchProcessor:
    """Process strategic search patterns from YAML configuration."""
    
    def __init__(self, yaml_path: Optional[Path] = None):
        """Initialize with YAML configuration file."""
        if yaml_path is None:
            # Default to strategic-searches.yaml in project root
            # Now in src/services/, so need to go up 2 levels to reach project root
            yaml_path = Path(__file__).parent.parent.parent / "strategic-searches.yaml"
            
        self.yaml_path = yaml_path
        self.patterns: Dict[str, SearchDomain] = {}
        self._load_patterns()
        
    def _load_patterns(self):
        """Load search patterns from YAML file."""
        try:
            with open(self.yaml_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                
            for domain_name, domain_data in data.items():
                searches = [
                    SearchPattern(**search_config) 
                    for search_config in domain_data.get('searches', [])
                ]
                self.patterns[domain_name] = SearchDomain(searches=searches)
                
            logger.info(f"Loaded {len(self.patterns)} search domains from {self.yaml_path}")
            
        except FileNotFoundError:
            logger.error(f"Strategic search configuration not found: {self.yaml_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML in strategic search configuration: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load strategic search patterns: {e}")
            raise
    
    def get_available_domains(self) -> List[str]:
        """Get list of available search domains."""
        return list(self.patterns.keys())
    
    def get_domain_searches(self, domain: str) -> List[SearchPattern]:
        """Get enabled search patterns for a domain."""
        if domain not in self.patterns:
            raise ValueError(f"Unknown search domain: {domain}. Available domains: {self.get_available_domains()}")
            
        return [search for search in self.patterns[domain].searches if search.enabled]
    
    def substitute_patterns(self, query: str, domain: str, max_searches: Optional[int] = None) -> List[Dict[str, str]]:
        """Generate search queries from patterns with substitution."""
        searches = self.get_domain_searches(domain)
        
        if not searches:
            raise ValueError(f"No enabled searches found for domain: {domain}")
            
        # Apply max_searches limit if specified
        if max_searches is not None:
            searches = searches[:max_searches]

        key_terms = extract_key_terms(query, max_terms=5)
        key_terms_str = " ".join(key_terms) if key_terms else query

        logger.debug(f"Extracted key terms: {key_terms}")
        
        substituted_searches = []
        for search in searches:
            try:
                # Perform template substitution
                formatted_query = search.query.format(
                    primary=query,
                    key_terms=key_terms_str
                )
                
                substituted_searches.append({
                    "name": search.name,
                    "query": formatted_query,
                    "description": search.description,
                    "original_pattern": search.query
                })
                
                logger.debug(f"Generated search '{search.name}': {formatted_query}")
                
            except KeyError as e:
                logger.warning(f"Template substitution failed for search '{search.name}': missing key {e}")
                continue
            except Exception as e:
                logger.warning(f"Error processing search pattern '{search.name}': {e}")
                continue
                
        if not substituted_searches:
            raise RuntimeError(f"No valid search patterns generated for domain '{domain}'")
            
        return substituted_searches
    
    def execute_strategic_search(
        self, 
        client: PineconeAssistantClient,
        params: StrategySearchParams
    ) -> Dict[str, Any]:
        """Execute strategic multi-search using the Assistant client."""
        
        # Validate domain
        if params.domain not in self.patterns:
            raise ValueError(f"Unknown search domain: {params.domain}. Available: {self.get_available_domains()}")
        
        # Generate search patterns
        search_patterns = self.substitute_patterns(
            params.query, 
            params.domain, 
            params.max_searches
        )
        
        logger.info(f"Executing {len(search_patterns)} strategic searches for domain '{params.domain}'")
        
        results = []
        errors = []
        
        for i, pattern in enumerate(search_patterns):
            try:
                logger.debug(f"Executing search {i+1}/{len(search_patterns)}: {pattern['name']}")
                
                # Create chat parameters for this search
                chat_params = AssistantChatParams(
                    messages=[Message(role="user", content=pattern["query"])],
                    model=params.model,
                    include_highlights=True,  # Always include highlights for strategic searches
                    stream=False  # Strategic searches don't use streaming
                )
                
                # Execute the search
                response = client.chat(chat_params)
                
                # Process the response
                if "message" in response and "content" in response["message"]:
                    result = {
                        "search_name": pattern["name"],
                        "search_description": pattern["description"],
                        "query": pattern["query"],
                        "response_content": response["message"]["content"],
                        "citations": response.get("citations", []),
                        "usage": response.get("usage", {}),
                        "model": response.get("model", params.model)
                    }
                    results.append(result)
                    
                    # Log successful search
                    usage = response.get("usage", {})
                    total_tokens = usage.get("total_tokens", "unknown")
                    logger.debug(f"Search '{pattern['name']}' completed, tokens: {total_tokens}")
                    
                else:
                    error_msg = f"Invalid response format for search '{pattern['name']}'"
                    logger.warning(error_msg)
                    errors.append(error_msg)
                    
            except Exception as e:
                error_msg = f"Search '{pattern['name']}' failed: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                
        # Compile results
        total_citations = sum(len(result.get("citations", [])) for result in results)
        total_tokens = 0
        for result in results:
            usage = result.get("usage", {})
            if isinstance(usage, dict):
                total_tokens += usage.get("total_tokens", 0)
            else:
                # Handle case where usage might be an object
                total_tokens += getattr(usage, "total_tokens", 0) if usage else 0
        
        strategic_result = {
            "query": params.query,
            "domain": params.domain,
            "searches_requested": len(search_patterns),
            "searches_completed": len(results),
            "searches_failed": len(errors),
            "results": results,
            "errors": errors if errors else None,
            "summary": {
                "total_citations": total_citations,
                "total_tokens": total_tokens,
                "successful_searches": [r["search_name"] for r in results],
                "failed_searches": [e for e in errors] if errors else None
            }
        }
        
        logger.info(f"Strategic search completed: {len(results)}/{len(search_patterns)} successful")
        
        return strategic_result
    
    def validate_domain(self, domain: str) -> bool:
        """Validate if a domain exists in the configuration."""
        return domain in self.patterns
    
    def get_domain_info(self, domain: str) -> Dict[str, Any]:
        """Get information about a specific domain."""
        if domain not in self.patterns:
            raise ValueError(f"Unknown domain: {domain}")
            
        domain_obj = self.patterns[domain]
        enabled_searches = [s for s in domain_obj.searches if s.enabled]
        
        return {
            "domain": domain,
            "total_searches": len(domain_obj.searches),
            "enabled_searches": len(enabled_searches),
            "search_patterns": [
                {
                    "name": s.name,
                    "description": s.description,
                    "enabled": s.enabled,
                    "query_template": s.query
                }
                for s in domain_obj.searches
            ]
        }