# Impact Engine Documentation

This directory contains the Sphinx documentation for Impact Engine.

## Local Development

### Prerequisites

```bash
pip install -r requirements.txt
```

### Building Documentation

```bash
# Build HTML documentation
make html

# Clean build files
make clean

# Live reload during development (requires sphinx-autobuild)
pip install sphinx-autobuild
make livehtml
```

The built documentation will be available in `_build/html/index.html`.

## GitHub Pages Deployment

Documentation is automatically built and deployed to GitHub Pages when changes are pushed to the main branch. The workflow is defined in `.github/workflows/docs.yml`.

## Structure

- `index.md` - Main documentation homepage
- `user-stories.md` - User stories and acceptance criteria
- `design.md` - Design principles and architecture
- `data-abstraction-layer.md` - Metrics layer documentation
- `modeling-abstraction-layer.md` - Models layer documentation
- `conf.py` - Sphinx configuration
- `requirements.txt` - Python dependencies for building docs