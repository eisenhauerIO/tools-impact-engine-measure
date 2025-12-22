# Documentation Maintenance Workflow

This guide ensures documentation stays organized, accurate, and free from redundancy.

## Content Ownership Matrix

Each piece of content has a single source of truth. When updating documentation, always update the primary location first, then update cross-references if needed.

| Content | Primary Location | Cross-references Allowed |
|---------|------------------|--------------------------|
| User stories | [user-stories.md](../../documentation/user-stories.md) | [README.md](../../README.md) (1-line summary) |
| Configuration | [configuration.md](../../documentation/configuration.md) | [user-stories.md](../../documentation/user-stories.md) (in examples) |
| Architecture & design | [design.md](../../documentation/design.md) | None - technical reference only |
| API reference | [api_reference.rst](../../documentation/api_reference.rst) | Auto-generated from code |

> **Note**: External dependencies like `artifact-store` and `online_retail_simulator` (catalog generator) are maintained in separate repositories on GitHub. See [pyproject.toml](../../pyproject.toml) for links.

## Update Workflow

When updating documentation, follow these steps:

### 1. Identify Content Owner

Check the matrix above to find where content should be updated.

### 2. Update Primary Location

Make your changes in the primary location first.

### 3. Verify Against Actual Code

**CRITICAL**: Before finalizing documentation changes, verify all examples match the actual codebase:

**For API Documentation**:
- Check API signatures in `science/impact_engine/__init__.py` for public API
- Verify function parameters match actual implementation
- Test code examples actually run without errors
- Verify data schemas match actual DataFrame outputs

**For Configuration Documentation** (configuration.md):
- Verify all parameter names match config parsing in `science/impact_engine/config.py`
- Verify default values match actual defaults
- Test configuration examples with actual config processor

**Common verification points**:
- `evaluate_impact()` signature matches documentation
- MetricsManager and ModelsManager APIs match documented interfaces
- Configuration keys are case-sensitive

### 4. Update Cross-References

If content is cross-referenced elsewhere:
- Use links, not duplication
- Keep summaries brief (1-4 lines maximum)
- Always point to the primary location for details

### 5. Verify Changes

Before committing documentation updates:
- Build Sphinx docs locally: `cd documentation && make html`
- Check for broken links (manually review)
- Verify all code examples work
- Review against this workflow

## Prohibited Patterns

To prevent documentation drift, **DO NOT**:

- Duplicate code examples across files
- Duplicate configuration blocks
- Duplicate schema tables
- Duplicate user stories

**Right approach**: Put complete content in primary location, link from others.

## Best Practices

### Link Instead of Duplicate

```markdown
<!-- Good: In README.md -->
For complete configuration options, see the [Configuration Reference](documentation/configuration.md).

<!-- Bad: In README.md -->
Here's all the configuration options... [300 lines of duplication]
```

### Summary + Link Pattern

```markdown
<!-- Good: In README.md -->
- **Data Scientists**: Generate realistic e-commerce data for ML model training

[See user stories](documentation/user-stories.md)

<!-- Bad: In README.md -->
[Full detailed user story duplicated from user-guide.md]
```

### One Example, Link for More

```markdown
<!-- Good: In README.md -->
```python
from impact_engine import evaluate_impact
result = evaluate_impact(config_path="config.yaml", storage_url="results/")
```

For more examples, see the [User Stories](documentation/user-stories.md).
```

## Review Checklist

Before committing documentation changes, verify:

### Content Review
- [ ] No duplicate code examples across files
- [ ] No duplicate configuration blocks
- [ ] No duplicate schema definitions
- [ ] Cross-references use links, not duplication
- [ ] New content follows the Content Ownership Matrix

### Technical Review
- [ ] Code verified against actual implementation
- [ ] API signatures match `science/impact_engine/__init__.py`
- [ ] Function parameters match actual implementations
- [ ] Configuration keys match actual config processor
- [ ] All code examples are tested and work

### Build Validation
- [ ] `cd documentation && make html` succeeds
- [ ] Generated HTML renders correctly
- [ ] Navigation works in built docs

### User Experience
- [ ] Information is easy to find
- [ ] Examples progress from simple to complex
- [ ] Cross-references help rather than confuse

## When to Update This Workflow

Update this workflow when:
- Adding new documentation files
- Changing documentation structure
- Adding new content types
- Modifying the single source of truth for any content
