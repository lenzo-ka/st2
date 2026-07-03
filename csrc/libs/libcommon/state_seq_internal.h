/**
 * @file state_seq_internal.h
 * @brief Private helpers shared by state_seq.c and state_seq_graph.c.
 *
 * Not part of any public API. Only callers inside libcommon include
 * this header. It exists to avoid duplicating the two pointer-plumbing
 * helpers that both state_seq_make() and state_seq_make_graph() need.
 */

#ifndef STATE_SEQ_INTERNAL_H
#define STATE_SEQ_INTERNAL_H

#include <s3/state.h>
#include <sphinxbase/prim_type.h>

/*
 * Wire state[s]'s next-state slice into the packed next_state[] /
 * next_tprob[] arrays at offset *n, then advance *n by n_next[s].
 * If n_next[s] == 0, leaves the pointers as zeroed by ckd_calloc().
 */
void
state_seq_set_next(state_t *state,
                   uint32 s,
                   const uint32 *n_next,
                   uint32 *next_state,
                   float32 *next_tprob,
                   uint32 *n);

/*
 * Symmetric to state_seq_set_next() for the prior-state slice.
 */
void
state_seq_set_prior(state_t *state,
                    uint32 s,
                    const uint32 *n_prior,
                    uint32 *prior_state,
                    float32 *prior_tprob,
                    uint32 *p);

#endif /* STATE_SEQ_INTERNAL_H */
