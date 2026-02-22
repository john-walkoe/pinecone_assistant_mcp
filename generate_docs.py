#!/usr/bin/env python3
"""
Generate documentation snippets from strategic-searches.yaml for forked repositories.

This script reads the strategic-searches.yaml file and generates documentation
snippets that can be used to update README.md and other documentation files
when the search domains are customized.

Usage:
    python generate_docs.py
    
Output:
    - Prints README domain list section
    - Prints Claude Desktop domain list 
    - Prints usage examples template
"""

import yaml
from pathlib import Path
from typing import Dict, List

def load_search_config() -> Dict:
    """Load search configuration from YAML."""
    config_path = Path(__file__).parent / "strategic-searches.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def generate_readme_domain_list(config: Dict) -> str:
    """Generate the domain list section for README.md."""
    lines = ["**Available domains** optimized for workflow efficiency:"]
    
    for domain_name, domain_data in config.items():
        searches = domain_data.get('searches', [])
        enabled_searches = [s for s in searches if s.get('enabled', True)]
        
        # Create summary from first few search descriptions
        if enabled_searches:
            descriptions = []
            for search in enabled_searches[:2]:  # First 2 searches
                desc = search.get('description', search.get('name', ''))
                # Extract key terms from description
                if 'Section' in desc:
                    descriptions.append('Section ' + desc.split('Section ')[1].split(' ')[0])
                elif 'PTAB' in desc:
                    descriptions.append('PTAB')
                elif 'examination' in desc.lower():
                    descriptions.append('examination')
                elif 'petition' in desc.lower():
                    descriptions.append('petitions')
                elif 'appeal' in desc.lower():
                    descriptions.append('appeals')
                    
            summary = ', '.join(descriptions) if descriptions else 'specialized searches'
            lines.append(f"- **`{domain_name}`**: {summary}, {len(enabled_searches)} targeted searches")
        else:
            lines.append(f"- **`{domain_name}`**: (no enabled searches)")
    
    return '\n'.join(lines)

def generate_claude_desktop_domains(config: Dict) -> str:
    """Generate domain list for Claude Desktop tool descriptions."""
    lines = []
    
    for domain_name, domain_data in config.items():
        searches = domain_data.get('searches', [])
        enabled_searches = [s for s in searches if s.get('enabled', True)]
        
        if enabled_searches:
            # Use search names for concise description
            search_names = [s.get('name', '').replace('_', ' ') for s in enabled_searches[:2]]
            summary = ', '.join(search_names)
            if len(enabled_searches) > 2:
                summary += f", +{len(enabled_searches) - 2} more"
            lines.append(f"            - **{domain_name}**: {summary} ({len(enabled_searches)} searches)")
    
    return '\n'.join(lines)

def generate_usage_examples(config: Dict) -> str:
    """Generate usage examples template."""
    lines = ["# Usage Examples\n"]
    
    for i, (domain_name, domain_data) in enumerate(config.items(), 1):
        searches = domain_data.get('searches', [])
        enabled_searches = [s for s in searches if s.get('enabled', True)]
        
        if enabled_searches:
            lines.append(f"## Example {i}: {domain_name.replace('_', ' ').title()}")
            lines.append(f"")
            lines.append(f"```json")
            lines.append(f'{{')
            lines.append(f'  "tool": "assistant_strategic_multi_search_chat",')
            lines.append(f'  "arguments": {{')
            lines.append(f'    "query": "your research question here",')
            lines.append(f'    "domain": "{domain_name}",')
            lines.append(f'    "max_searches": {min(3, len(enabled_searches))}')
            lines.append(f'  }}')
            lines.append(f'}}')
            lines.append(f"```")
            lines.append(f"")
            lines.append(f"**Triggers**: {', '.join([s.get('name', '') for s in enabled_searches])}")
            lines.append(f"")
    
    return '\n'.join(lines)

def main():
    """Generate all documentation snippets."""
    config = load_search_config()
    
    print("=" * 60)
    print("STRATEGIC SEARCH DOCUMENTATION GENERATOR")
    print("=" * 60)
    print()
    
    print("README.md Domain List Section:")
    print("-" * 40)
    print(generate_readme_domain_list(config))
    print()
    
    print("Claude Desktop Tool Description:")
    print("-" * 40) 
    print(generate_claude_desktop_domains(config))
    print()
    
    print("Usage Examples Template:")
    print("-" * 40)
    print(generate_usage_examples(config))
    print()
    
    print("Instructions:")
    print("- Copy the sections above to update your documentation")
    print("- Customize the descriptions to match your domain content")
    print("- Run this script whenever you modify strategic-searches.yaml")
    print()

if __name__ == "__main__":
    main()