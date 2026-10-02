/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Copyright (C) 2026 SnapKitty Collective */
/* Goldilocks field: p = 2^64 - 2^32 + 1. Mirrors sable/field.py exactly. */
#ifndef SABLE_FIELD_H
#define SABLE_FIELD_H

#include <stdint.h>

static const unsigned __int128 P128 = (unsigned __int128)18446744069414584321ULL; /* 2^64-2^32+1 */
#define P_U64 18446744069414584321ULL
#define HALF_U64 0x8000000000000000ULL

static inline uint64_t gf_add(uint64_t a, uint64_t b) {
    unsigned __int128 s = (unsigned __int128)a + b;
    if (s >= P128) s -= P128;
    return (uint64_t)s;
}

static inline uint64_t gf_sub(uint64_t a, uint64_t b) {
    unsigned __int128 d = (unsigned __int128)a - b;
    if (a < b) d += P128;
    return (uint64_t)d;
}

static inline uint64_t gf_mul(uint64_t a, uint64_t b) {
    return (uint64_t)(((unsigned __int128)a * b) % P128);
}

/* Signed interpretation of a 64-bit representative (the SUBLEQ test domain). */
static inline int64_t to_signed(uint64_t x) {
    if (x >= HALF_U64)
        return (int64_t)(x - HALF_U64) - (int64_t)HALF_U64;
    return (int64_t)x;
}

#endif
