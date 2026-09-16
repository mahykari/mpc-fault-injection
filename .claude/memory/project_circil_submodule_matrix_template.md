---
name: project-circil-submodule-matrix-template
description: "circil upgraded to the new template system; Matrix needs no circil patch, but unit 1 must be rewritten"
metadata: 
  node_type: memory
  type: project
  originSessionId: 526aa541-ccaa-4f4e-ba7f-4e9c4b7f49ba
  modified: 2026-08-14T22:40:49.695Z
---

Superseded twice. Current state as of 2026-08-15:

`python-circil/` is now a real clone of
`git@github.com:Rigorous-Software-Engineering/python-circil.git` (branch `main`),
dropped in on 2026-08-12. The previous vendored copy is at `python-circil.old/`.
It stays gitignored; changes to it go in patches under `patches/`, the same way
`patches/mpspdz/` works. The `circil-submodule` branch is moot.

**No circil patch is needed for Matrix.** The new circil has a real extension
point: `circil/ir/templates.py` (`TemplateType.resolve_type`,
`extract_mappings`) and `BaseParser.register_templated_type` for using custom
types in rewrite patterns. Exemplars: `circil/extensions/types/sized_string/`
(one value param, the pattern Mahyar names) and
`circil/extensions/types/tuple2/` (two params, plus a `rules.py`). So `matmul`
declaring `m,k,n` over `MatrixTemplate` is directly expressible.

**But unit 1 is written against the old API and is red.** `pipeline/matrix.py`
(commit 688508f on `matrix-rewrites`) relies on `Custom.constructor()` being an
instance method to bake shapes into the type name. In the new circil it is a
`@staticmethod` returning a templated spec, so config validation dies with
`Matrix.constructor() missing 1 required positional argument: 'self'`.
Unit 1 needs rewriting, not patching.

Also renamed in the new circil: `enable_fixed_size_array` -> `enable_array`,
`array_types_for_fixed_size_array` -> `array_element_types`.
