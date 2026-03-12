# ADR-001: Jinja2 as Template Engine

## Status
Accepted

## Context
Code generators for embedded systems need a template layer that separates
algorithmic structure from output syntax. MATLAB Embedded Coder uses TLC
(Target Language Compiler), a proprietary template language tightly coupled
to Simulink's intermediate representation (.rtw files). We need an
equivalent that is open, well-documented, and widely understood.

Alternatives considered:
- **String concatenation** — fragile, no control flow, unmaintainable past
  a handful of files.
- **Mako** — capable but less popular; smaller community, weaker IDE support.
- **Jinja2** — mature, battle-tested in web frameworks, supports
  inheritance, macros, whitespace control, and custom filters.

## Decision
Use Jinja2 as the template engine. Templates live in `templates/` and
mirror the TLC file-per-output-artifact pattern: one `.j2` template per
generated C file, with block-level fragments in `templates/blocks/`.

## Consequences
- Templates are readable by anyone familiar with Django/Flask templating.
- Whitespace control (`{%- -%}`) is essential for clean C output; template
  authors must understand Jinja2 whitespace semantics.
- The engine passes a context dict whose keys must stay in sync with
  template variable references — changes to either side require updating
  the other.
