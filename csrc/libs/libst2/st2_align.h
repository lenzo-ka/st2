/**
 * @file st2_align.h
 * @brief In-process forced alignment API for st2 (CFFI binding target).
 *
 * Thin session wrapper over the sphinx3 forced aligner vendored under
 * csrc/programs/sphinx3_align. Replaces the subprocess-based wrapper in
 * st2/lib/alignment/sphinx3.py and the PocketSphinx-based wrapper in
 * st2/lib/alignment/core.py.
 *
 * Lifetime: one aligner instance per process. The underlying C aligner
 * holds module-static state; a second concurrent st2_align_init while a
 * context is still alive returns NULL.
 */

#ifndef ST2_ALIGN_H
#define ST2_ALIGN_H

#include <sphinxbase/prim_type.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct st2_align_config_s {
    double  beam;            /**< Main pruning beam.        Default 1e-64. */
    int     insert_sil;      /**< Insert optional silences. Default 1.    */
    int     compute_phones;  /**< Return phone segments.    Default 1.    */
    int     compute_states;  /**< Return state segments.    Default 0.    */
    const char *feat_type;   /**< Feature stream spec.   Default "1s_c_d_dd". */
    const char *cmn;         /**< CMN type.              Default "current". */
    const char *agc;         /**< AGC type.              Default "none".    */
    int     varnorm;         /**< Cepstral variance norm.   Default 0.    */
    int     frate;           /**< Frame rate (Hz).          Default 100.  */
    int     lts_mismatch;    /**< Use LTS rules for OOV.    Default 0.    */
} st2_align_config_t;

void st2_align_config_default(st2_align_config_t *config);

typedef struct st2_align_context_s st2_align_context_t;

typedef struct st2_align_seg_s {
    const char *name;    /**< Word/phone/state label (owned by result). */
    int32 start_frame;
    int32 end_frame;
    int32 score;
} st2_align_seg_t;

typedef struct st2_align_result_s {
    st2_align_seg_t *words;
    uint32 n_words;
    st2_align_seg_t *phones;
    uint32 n_phones;
    st2_align_seg_t *states;
    uint32 n_states;
    int32 total_score;
    int32 n_frames;
    void   *_arena;        /**< Internal: string storage. Don't touch. */
} st2_align_result_t;

/**
 * Initialize a forced-alignment session.
 *
 * @param mdef_path Model definition file.
 * @param mean_path Means file.
 * @param var_path  Variances file.
 * @param mixw_path Mixture weights file.
 * @param tmat_path Transition matrices file.
 * @param feat_params_path Optional feat.params file (may be NULL); when
 *        present overrides feat/cmn/agc/varnorm from the config struct
 *        the way the standalone sphinx3_align does.
 * @param dict_path Main dictionary.
 * @param fdict_path Filler dictionary (may be NULL).
 * @param config Tunables (NULL for defaults).
 * @return Opaque context, or NULL on failure (see st2_align_last_error).
 */
st2_align_context_t *
st2_align_init(const char *mdef_path,
               const char *mean_path,
               const char *var_path,
               const char *mixw_path,
               const char *tmat_path,
               const char *feat_params_path,
               const char *dict_path,
               const char *fdict_path,
               const st2_align_config_t *config);

/**
 * Tear down a forced-alignment session.
 */
void st2_align_free(st2_align_context_t *ctx);

/**
 * Align one utterance from already-extracted MFCC frames.
 *
 * @param ctx Context.
 * @param mfcc Row-major MFCC matrix, shape (n_frames, ncep).
 * @param n_frames Number of MFCC frames.
 * @param ncep Number of cepstral coefficients per frame.
 * @param transcript Reference transcript (word sequence, may include the
 *        usual sphinx <s>/</s> markers; they will be stripped).
 * @param utt_id Utterance id (for logging; may be NULL).
 * @param out_result Out: result struct. Free with st2_align_result_free.
 * @return 0 on success, negative on failure.
 */
int
st2_align_mfcc(st2_align_context_t *ctx,
               const float *mfcc,
               uint32 n_frames,
               uint32 ncep,
               const char *transcript,
               const char *utt_id,
               st2_align_result_t **out_result);

/**
 * Align one utterance from a cepstrum file on disk (.mfc / sphinx2 binary
 * cepstra). Convenient for parity-checking against the standalone
 * sphinx3_align binary.
 */
int
st2_align_mfc_file(st2_align_context_t *ctx,
                   const char *mfc_path,
                   const char *transcript,
                   const char *utt_id,
                   st2_align_result_t **out_result);

/**
 * Free a result struct returned by st2_align_mfcc / st2_align_mfc_file.
 */
void st2_align_result_free(st2_align_result_t *result);

/**
 * Return the most recent error message recorded by st2_align, or NULL if
 * nothing has gone wrong. Pointer is owned by the library; valid until
 * the next st2_align_* call.
 */
const char *st2_align_last_error(void);

#ifdef __cplusplus
}
#endif

#endif /* ST2_ALIGN_H */
