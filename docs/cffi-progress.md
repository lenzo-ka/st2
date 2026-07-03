# CFFI Wrapper Progress

This document tracks the status of CFFI wrappers for ST2 C library functionality.

## Summary

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1: CI Training | ✅ Complete | Single Gaussian HMM training |
| Phase 2: Gaussian Splitting | ✅ Complete | Multi-density CI models |
| Phase 3: CD Model Building | ✅ Complete | Triphones, decision trees, state tying |
| Phase 4: Adaptation | ✅ Complete | MLLR ✅, MAP ✅ |
| Phase 5: Utilities | ✅ Complete | Alignment ✅, cepview/printp ✅, delint/kdtree/map ✅ |

**All CFFI wrappers complete!** Full CI→CD model building pipeline and adaptation are wrapped.

## Legend
- ✅ Done and tested
- 🔄 Partially done / needs work
- ❌ Not started
- 🔜 Next priority

---

## Phase 1: CI Model Training (Single Gaussian)

### Core I/O
| Component | C Function/File | CFFI Status | Python Wrapper | Notes |
|-----------|-----------------|-------------|----------------|-------|
| Gaussian read | `s3gau_read` | ✅ | `_st2c.read_gau()` | |
| Gaussian write | `s3gau_write` | ✅ | `_st2c.write_gau()` | |
| Mixw read | `s3mixw_read` | ✅ | `_st2c.read_mixw()` | |
| Mixw write | `s3mixw_write` | ✅ | `_st2c.write_mixw()` | |
| Tmat read | `s3tmat_read` | ✅ | `_st2c.read_tmat()` | |
| Tmat write | `s3tmat_write` | ✅ | `_st2c.write_tmat()` | |
| Mdef read | `model_def_read` | ✅ | Direct CFFI | |
| Mdef write | `model_def_write` | ✅ | Direct CFFI | |

### Feature Extraction (`sphinx_fe`)
| Component | C Function/File | CFFI Status | Python Wrapper | Notes |
|-----------|-----------------|-------------|----------------|-------|
| FE init | `fe_init_auto` | ✅ | Direct CFFI | |
| FE init custom | `st2_fe_create` | ✅ | `features.FeatureExtractor` | Custom helper |
| FE process | `fe_process_frames` | ✅ | `features.FeatureExtractor` | |
| Feat init | `feat_init` | ✅ | Direct CFFI | |
| Feat compute | `feat_s2mfc2feat_live` | ✅ | Direct CFFI | |

### Flat Model Initialization (`mk_flat`, `init_gau`, `norm`)
| Component | C Function/File | CFFI Status | Python Wrapper | Notes |
|-----------|-----------------|-------------|----------------|-------|
| Create tmat | `st2_flat_tmat` | ✅ | `flat.create_transition_matrices()` | Via CFFI |
| Create mixw | `st2_flat_mixw` | ✅ | `flat.create_mixture_weights()` | Via CFFI |
| Init Gaussians | `st2_init_gau` | ✅ | `flat.init_gaussians()` | Via CFFI |
| Normalize | `st2_norm_gau` | ✅ | `flat.normalize_gaussians()` | Via CFFI |
| Mdef (text) | N/A | ✅ | `flat.create_mdef()` | Config file (text) |
| Topology (text) | N/A | ✅ | `flat.create_topology_file()` | Config file (text) |

> **Note**: Mdef and topology are plain text config files, not binary model parameters.
> Python generates these as simple string formatting - no algorithm reimplementation.

### Baum-Welch Training (`bw`)
| Component | C Function/File | CFFI Status | Python Wrapper | Notes |
|-----------|-----------------|-------------|----------------|-------|
| BW init | `st2_bw_init` | ✅ | Direct CFFI | |
| BW free | `st2_bw_free` | ✅ | Direct CFFI | |
| Set dictionary | `st2_bw_set_dict` | ✅ | Direct CFFI | |
| Process utt (phones) | `st2_bw_process_utt` | ✅ | Direct CFFI | |
| Process utt (text) | `st2_bw_process_utt_text` | ✅ | Direct CFFI | |
| Normalize | `st2_bw_normalize` | ✅ | Direct CFFI | |
| Save params | `st2_bw_save` | ✅ | Direct CFFI | |
| Get stats | `st2_bw_get_stats` | ✅ | Direct CFFI | |

### Notes
- All binary model parameters (tmat, mixw, means, vars) created via CFFI
- Mdef/topology are text config files generated in Python (simple formatting, not algorithm)
- ⚠️ BW with uninitialized model may have numerical issues - use `init_gaussians()` with real feature data

---

## Phase 2: CI Gaussian Splitting (Multiple Densities) ✅

Increase from 1 Gaussian per state to N Gaussians (typically 8-64).

### Required Components
| Component | C Program | CFFI Status | Priority | Notes |
|-----------|-----------|-------------|----------|-------|
| K-means clustering | `k_means` (in lib) | ✅ | - | `split.kmeans()` |
| Increase components | `st2_inc_comp` | ✅ | - | `split.split_gaussians()` |
| Denom read/write | `s3gaudnom_*` | ✅ | - | `_st2c.read/write_dnom()` |
| K-means init | `st2_kmeans_init` | ✅ | - | `split.kmeans_init_gaussians()` |

### Workflow
1. Train CI model with 1 Gaussian (Phase 1) ✅
2. `st2_inc_comp` - Split each Gaussian into 2 ✅
3. `st2_kmeans_init` - Re-cluster features (optional) ✅
4. BW training with new density count ✅
5. Repeat 2-4 until target density (8, 16, 32, etc.)

### Completed CFFI Wrappers
```
[x] st2_inc_comp() - Gaussian splitting
[x] st2_kmeans() - K-means clustering
[x] st2_kmeans_init() - K-means Gaussian initialization (means, vars, weights)
```

---

## Phase 3: CD Model Building (Context-Dependent)

Build triphone models with state tying.

### 3a. Triphone Generation ✅
| Component | C Program | CFFI Status | Priority | Notes |
|-----------|-----------|-------------|----------|-------|
| Generate CI mdef | `st2_mdef_gen_ci` | ✅ | - | `mdef.generate_ci_mdef()` |
| Generate all triphones | `st2_mdef_gen_alltriphones` | ✅ | - | `mdef.generate_alltriphones_mdef()` |
| Generate untied mdef | `st2_mdef_gen_untied` | ✅ | - | `mdef.generate_untied_mdef()` |
| Count triphones | `st2_mdef_count_triphones` | ✅ | - | `mdef.count_triphones()` |
| Acmod set | `acmod_set_*` | ✅ | - | Already wrapped |

### 3b. Decision Tree Building
| Component | C Program | CFFI Status | Priority | Notes |
|-----------|-----------|-------------|----------|-------|
| Make questions | `st2_make_quests` | ✅ | - | `dtree.make_quests()` |
| Build tree | `st2_build_tree` | ✅ | - | `dtree.build_tree()` |
| Read pset | `st2_read_pset` | ✅ | - | Direct CFFI |
| Prune tree | `st2_prune_tree` | ✅ | - | `dtree.prune_tree()` |

### 3c. State Tying
| Component | C Program | CFFI Status | Priority | Notes |
|-----------|-----------|-------------|----------|-------|
| Tie states | `st2_tie_states` | ✅ | - | `dtree.tie_states()` |
| TS2CB mapping | `s3ts2cb_*` | ✅ | - | `ts2cb.py` |

### 3d. CD Training
| Component | C Program | CFFI Status | Priority | Notes |
|-----------|-----------|-------------|----------|-------|
| Aggregate segments | `st2_agg_seg` | ✅ | - | `agg_seg.aggregate_segments()` |
| Parameter counting | `st2_param_cnt` | ✅ | - | `param_cnt.count_params()` |
| BW for CD | `bw` | ✅ | - | Same as CI |
| Norm for CD | `norm` | ✅ | - | Same as CI |

### Workflow
1. CI model training complete ✅
2. Generate all possible triphones from dictionary (`mk_mdef_gen`) ✅
3. Generate phonetic questions (`make_quests`) ✅ (CFFI)
4. Accumulate stats by phone/state (`agg_seg`) ✅ (CFFI)
5. Build decision trees (`bldtree`) ✅ (CFFI)
6. Tie states using trees (`tiestate`) ✅ (CFFI)
7. Initialize CD model from CI (`mk_ts2cb`) ✅ (CFFI)
8. BW training on CD model ✅
9. Gaussian splitting on CD model (Phase 2) ✅

### Completed CFFI Wrappers
```
[x] st2_mdef_gen_*() - Generate CI, triphone, and untied model definitions
[x] st2_make_quests() - Generate phonetic questions
[x] st2_build_tree() - Build decision tree
[x] st2_read_pset() - Read phone set files
[x] st2_tie_states() - Apply state tying
[x] s3ts2cb_*() - Tied-state to codebook mapping
[x] st2_prune_tree() - Prune decision tree
[x] st2_agg_seg() - Aggregate segmentation statistics
[x] st2_param_cnt() - Parameter counting
```

---

## Phase 4: Adaptation (Optional) ✅

Speaker/environment adaptation.

| Component | C Program | CFFI Status | Priority | Notes |
|-----------|-----------|-------------|----------|-------|
| MAP adaptation | `st2_map_adapt` | ✅ | - | `map_adapt.map_adapt()` |
| MLLR classes | `mllr_class_read/write` | ✅ | - | Class mapping I/O |
| MLLR solve | `compute_mllr` | ✅ | - | Compute MLLR matrices |
| MLLR transform | `mllr_transform_mean` | ✅ | - | Apply transform to means |
| MLLR I/O | `store_reg_mat/read_reg_mat` | ✅ | - | Matrix I/O |
| CB2MLLR I/O | `s3cb2mllr_read/write` | ✅ | - | Codebook to MLLR mapping |
| MLLR free | `free_mllr_A/B/reg` | ✅ | - | Memory cleanup |

---

## Phase 5: Utilities & Diagnostics ✅

| Component | C Program | Status | Priority | Notes |
|-----------|-----------|--------|----------|-------|
| Forced alignment | `pocketsphinx` | ✅ | - | Via pocketsphinx Python bindings (Cython) |
| Forced alignment | `sphinx3_align` | ✅ | LOW | Shell-out for parity checking only |
| View cepstra | `sphinx_cepview` | ✅ | - | Native Python + shell-out for parity |
| Print params | `printp` | ✅ | - | Native Python + shell-out for parity |
| Delint | `st2_delint` | ✅ | - | `delint.deleted_interpolation()` |
| KD-tree | `st2_kdtree_build` | ✅ | - | `kdtree.build_kdtree()` |
| MAP adaptation | `st2_map_adapt` | ✅ | - | `map_adapt.map_adapt()` |

### Alignment Notes
- **PocketSphinx** (preferred): Python bindings, `pip install pocketsphinx`
- **sphinx3_align**: Shell-out wrapper for parity checking
- Both exposed via the `st2.lib.alignment` package:
  - `core` — single-utterance PocketSphinx alignment (`align_utterance`, `pocketsphinx_align`)
  - `batch` — corpus alignment (`align_corpus`, `AlignmentJob`, `load_transcripts`)
  - `sphinx3` — shell-out wrapper (`sphinx3_align`)
  - `export` — TextGrid / CTM / Sphinx-segment writers (`to_textgrid`, `to_ctm`, `to_sphinx_segments`, `save_textgrid`, `save_ctm`)

### Debugging Tools Notes
- **sphinx_cepview**: `st2.lib.cepview` - native Python + shell-out
- **printp**: `st2.lib.printp` - native Python + shell-out
- Both have parity checking between implementations

---

## Implementation Priority Order

### Immediate (CI Gaussian Splitting) ✅ COMPLETE
1. ~~`st2_inc_comp` - Gaussian splitting~~ ✅ Done
2. ~~`st2_kmeans` - K-means clustering~~ ✅ Done
3. ~~`st2_kmeans_init` - Feature clustering + variance + weights~~ ✅ Done

### Short-term (CD Foundation) ✅ COMPLETE
4. ~~`st2_mdef_gen_*` - Triphone generation~~ ✅ Done (CFFI)
5. ~~`st2_make_quests` - Question generation~~ ✅ Done (CFFI)
6. ~~`st2_build_tree` - Decision tree building~~ ✅ Done (CFFI)
7. ~~`st2_tie_states` - State tying~~ ✅ Done (CFFI)

### Medium-term (CD Complete) ✅
8. ~~`st2_agg_seg` - Segment aggregation~~ ✅ Done
9. ~~`st2_mk_ts2cb` - Codebook mapping~~ ✅ Done
10. ~~`st2_prune_tree` - Tree pruning~~ ✅ Done

### Long-term (Polish) ✅ COMPLETE
11. ~~Forced alignment~~ ✅ Done (PocketSphinx + sphinx3_align shell-out)
12. ~~View cepstra / Print params~~ ✅ Done (Native Python + shell-out)
13. ~~`delint`~~ ✅ Done (CFFI - smooths mixture weights)
14. ~~`kdtree`~~ ✅ Done (CFFI - fast Gaussian selection)
15. ~~`map_adapt`~~ ✅ Done (CFFI - MAP speaker adaptation)

**All CFFI wrappers complete!**

---

## CLI Dry-Run Support

The CLI supports `--dry-run` (`-n`) mode which emits shell commands instead of executing:

```bash
st2 --dry-run flat --project-dir ./my_project
```

This generates a bash script that can be:
- Reviewed before execution
- Saved and run later
- Used for debugging or CI integration

### ST2 Actions in CLI

The CLI includes action classes that emit proper shell commands:

| Action | Shell Command | Notes |
|--------|--------------|-------|
| `FeatureExtractAction` | `sphinx_fe` | Feature extraction |
| `BaumWelchAction` | `bw` | Baum-Welch training |
| `NormAction` | `norm` | Normalize accumulators |
| `SplitGaussiansAction` | `inc_comp` | Gaussian splitting |
| `MakeQuestsAction` | `make_quests` | Question generation |
| `BuildTreeAction` | `bldtree` | Decision tree building |
| `TieStatesAction` | `tiestate` | State tying |
| `AggSegAction` | `agg_seg` | Segment aggregation |

---

## Parity Testing

Parity tests in `tests/test_parity.py` verify that:

1. **I/O roundtrips** - CFFI read/write preserve data
2. **Shell-out vs CFFI** - Both produce identical results
3. **CLI dry-run** - Emitted commands are valid bash

Tests are skipped when SphinxTrain binaries are not available.

---

## Notes

### Design Principles
- Prefer CFFI over shelling out to binaries
- Never reimplement complex C algorithms in Python
- Hierarchy: CFFI (preferred) > Shell out > Python native (only for simple logic)

### Testing Strategy
- Each CFFI wrapper should have round-trip tests
- Parity tests compare shell-out vs CFFI results
- CLI dry-run tests validate generated bash scripts

### Files
- C wrappers: `csrc/libs/libst2/st2_*.c`
- Headers: `csrc/libs/libst2/st2_*.h`
- Python CFFI: `st2/lib/_st2c.py`
- Python wrappers: `st2/lib/*.py`
  - `delint.py` - Deleted interpolation
  - `kdtree.py` - KD-tree building
  - `map_adapt.py` - MAP adaptation
- CLI actions: `st2/cli/base.py`
- Parity tests: `tests/test_parity.py`
