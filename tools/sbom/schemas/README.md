# Vendored CycloneDX 1.5 JSON schemas

Used by `tools/make_sbom.py --validate` so that SBOM validation works offline
and against a fixed schema.

| File | Source | SHA-256 |
|---|---|---|
| `bom-1.5.schema.json` | https://raw.githubusercontent.com/CycloneDX/specification/1.5/schema/bom-1.5.schema.json | `067f7824b08653839ea050ae9e09ca48375eadc2652b0e2a299476e7db90335b` |
| `spdx.schema.json` | https://raw.githubusercontent.com/CycloneDX/specification/1.5/schema/spdx.schema.json | `4f6e2b05c05d26a4f2dc5879fbc2fca94b0a28db46289d0c51345621b71cfbfc` |
| `jsf-0.82.schema.json` | https://raw.githubusercontent.com/CycloneDX/specification/1.5/schema/jsf-0.82.schema.json | `8bae002c25e723db7ee1f26afde680ae1a2b1a8f6b4b4b0fd65dc3becb090aae` |

Downloaded 2026-10-24 from the `1.5` branch of the CycloneDX specification
repository. License: Apache License 2.0 (`LICENSE` in this directory). The
files are unmodified; they are SOUP of the build tooling, not of MiniDAQ.
