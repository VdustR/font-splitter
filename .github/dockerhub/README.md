# Font Splitter

Python library and CLI for splitting large font files into smaller `unicode-range` webfont subsets.

Font Splitter uses FontTools directly and can plan subsets from multiple ordered sources. For example, it can follow `unicode-range` declarations from a local font CSS file first, then place remaining codepoints into Unicode Block fallback ranges. It also supports the simpler Unicode Block plus `max_codepoints` flow for predictable default output.

## Current Package

This Docker image contains the Python implementation. Tags before `v0.2.0` contain the legacy Node.js implementation.

The npm package is deprecated and no longer maintained. Use the Python CLI/API, GitHub release assets, or this Docker image for current usage.

See the GitHub repository for installation, CLI examples, Python API usage, release notes, and font license guidance:

https://github.com/VdustR/font-splitter

## Quick Start

```sh
docker run --rm -v "$PWD:/fonts" vdustr/font-splitter:v0.2.1 input.ttf --output output
```

Published release tags use these forms:

- `vX.Y.Z`
- `X.Y.Z`
- `latest`
