# Customizing Strategic Search Domains

This MCP server is designed to be **fully customizable** for any document corpus and research domain. The strategic search functionality automatically adapts to whatever domains and search patterns you define in `strategic-searches.yaml`.

## 🎯 Complete Flexibility

**What's Dynamic**:
- ✅ Domain names (top-level YAML keys)
- ✅ Search patterns within domains
- ✅ Number of searches per domain
- ✅ Tool descriptions in Claude Desktop
- ✅ Domain validation
- ✅ Error messages

**What Never Needs Code Changes**:
- Adding new domains
- Removing domains
- Changing search patterns
- Enabling/disabling individual searches
- Modifying query templates

## 📝 YAML Structure

The `strategic-searches.yaml` file supports any structure following this pattern:

```yaml
your_domain_name:
  description: "Brief description of this domain's focus"
  searches:
    - name: "search_identifier"
      query: "search query with {primary} placeholder"
      description: "Human readable description"
      enabled: true
    - name: "another_search"
      query: "another query template {primary} {key_terms}"
      description: "Another description"
      enabled: true

another_domain:
  description: "Another domain description"
  searches:
    - name: "different_search"
      query: "different query for {primary}"
      description: "Different domain search"
      enabled: true

# Configuration settings (optional)
settings:
  default_results_per_search: 10
  default_domain: "your_domain_name"
  variable_extraction:
    key_terms_count: 3
  variables:
    primary: "The main subject being researched"
    key_terms: "Key terms extracted from primary subject"
```

## 🔧 Customization Examples

### Example 1: Medical Research MCP

```yaml
clinical_research:
  description: "Clinical guidelines and medical research"
  searches:
    - name: "clinical_guidelines"
      query: "{primary} clinical guidelines treatment protocol"
      description: "Search for established clinical practice guidelines"
      enabled: true
    - name: "fda_regulations"
      query: "FDA regulations {primary} medical device approval"
      description: "Find relevant FDA regulatory requirements"
      enabled: true
    - name: "literature_review"
      query: "{primary} peer reviewed research clinical studies"
      description: "Search peer-reviewed research literature"
      enabled: true
```

### Example 2: Financial Analysis MCP

```yaml
financial_analysis:
  description: "Financial analysis and regulatory compliance"
  searches:
    - name: "sec_filings"
      query: "{primary} 10-K 10-Q financial disclosures"
      description: "Search SEC filings and disclosures"
      enabled: true
    - name: "gaap_standards"
      query: "GAAP accounting standards {primary} financial reporting"
      description: "Generally Accepted Accounting Principles research"
      enabled: true
    - name: "risk_assessment"
      query: "{key_terms} financial risk assessment regulatory compliance"
      description: "Financial risk and compliance analysis"
      enabled: true
```

### Example 3: Legal Research MCP

```yaml
corporate_law:
  description: "Corporate law and securities regulations"
  searches:
    - name: "delaware_law"
      query: "Delaware corporate law {primary} case law precedent"
      description: "Search Delaware corporate law and precedents"
      enabled: true
    - name: "sec_regulations"
      query: "SEC regulations {primary} disclosure requirements"
      description: "Find relevant Securities and Exchange Commission rules"
      enabled: true
    - name: "corporate_governance"
      query: "{key_terms} corporate governance fiduciary duty board"
      description: "Board governance and fiduciary duty research"
      enabled: true
```

## 🚀 Quick Customization Steps

1. **Modify strategic-searches.yaml**:
   ```bash
   # Edit the domains and searches to match your content
   nano strategic-searches.yaml
   ```

2. **Generate updated documentation**:
   ```bash
   # Run the doc generator to get updated README snippets
   python generate_docs.py
   ```

3. **Update your documentation**:
   ```bash
   # Copy the generated snippets to README.md and other docs
   # Customize descriptions to match your specific domain
   ```

4. **Test the changes**:
   ```bash
   # Test with Claude Desktop or direct MCP calls
   # The server automatically loads your new domains
   ```

## 🔍 Template Variables

Your search queries can use these template variables:

- **`{primary}`**: The main query term from user input
- **`{key_terms}`**: Extracted keywords from the query (if keyword extraction is implemented)

### Advanced Template Examples

```yaml
advanced_search_domain:
  searches:
    - name: "comprehensive_analysis"
      query: "comprehensive analysis of {primary} including {key_terms} methodology"
      description: "Comprehensive analysis with methodology focus"
      enabled: true
    - name: "comparative_study"
      query: "comparative study {primary} versus alternatives {key_terms}"
      description: "Comparative analysis with alternatives"
      enabled: true
```

## 🛠️ Development Workflow

### For Document Corpus Changes

1. **Prepare your documents**: Upload to your Pinecone Assistant instance
2. **Design search domains**: Plan domains that match your content structure
3. **Create search patterns**: Write query templates that work with your content
4. **Test and iterate**: Refine searches based on result quality

### For New Research Areas

1. **Analyze content structure**: Understand how your documents are organized
2. **Map research workflows**: Identify how users will approach the content
3. **Design domain hierarchy**: Create logical groupings for different use cases
4. **Implement search patterns**: Write targeted queries for each domain

## 📊 Best Practices

### Domain Design

- **3-5 searches per domain**: Balances coverage with focused results
- **Workflow-aligned domains**: Match common user research patterns
- **Clear naming**: Use descriptive domain names (e.g., `section_101_eligibility`, `clinical_research`)
- **Logical grouping**: Group related searches together

### Search Pattern Design

- **Specific queries**: More focused searches yield better results
- **Template variables**: Use `{primary}` for full user query, `{key_terms}` for extracted keywords
- **Clear descriptions**: Help users understand what each search does
- **Enable/disable flags**: Test and refine searches without deletion

### Query Design Tips

- **Use domain terminology**: Include field-specific terms in queries
- **Combine broad + specific**: Mix general terms with specific concepts
- **Test iteratively**: Refine queries based on result quality
- **Consider search order**: Most important searches first in YAML

## 🔧 Advanced Customization

### Custom Keyword Extraction

You can implement custom keyword extraction by modifying the `StrategySearchProcessor` class:

```python
def extract_keywords(self, query: str) -> List[str]:
    """Extract keywords from user query for template substitution."""
    # Implement your keyword extraction logic
    # Return list of relevant terms
    pass
```

### Domain-Specific Processing

Add domain-specific logic in the search processor:

```python
def process_domain_specific(self, domain: str, query: str) -> str:
    """Apply domain-specific query processing."""
    if domain == "medical_research":
        # Add medical terminology enhancement
        pass
    elif domain == "financial_analysis":
        # Add financial context
        pass
    return query
```

### Custom Validation

Add custom domain validation:

```python
def validate_domain_config(self, domain_data: Dict) -> bool:
    """Validate domain configuration."""
    # Implement your validation logic
    # Check required fields, search patterns, etc.
    return True
```

## 📚 Migration from USPTO Content

If you're adapting this MCP for non-USPTO content:

1. **Replace document corpus**: Upload your documents to Pinecone Assistant
2. **Update search domains**: Replace patent law domains with your content areas
3. **Revise search patterns**: Write queries appropriate for your content
4. **Update documentation**: Use `generate_docs.py` to create new documentation
5. **Customize descriptions**: Update README and examples to match your use case

## 🎯 Result

With these customizations, you'll have a fully tailored MCP server that:

- ✅ Automatically adapts to your domain structure
- ✅ Provides domain-specific search patterns
- ✅ Generates appropriate Claude Desktop tool descriptions
- ✅ Validates user input against your available domains
- ✅ Requires zero code changes for content modifications

The strategic search system becomes a **universal document research interface** that can be adapted to any knowledge domain or document corpus.