/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Copyright (C) 2026 SnapKitty Collective */
/* SplitMix64, counter-increment threading (state += gamma BEFORE mix).
   Mirrors sable/stream.py. seed 0x00BEEFCAFE, n=1024 -> checksum 1388262917130611548. */
#ifndef SABLE_SPLITMIX_H
#define SABLE_SPLITMIX_H

#include <stdint.h>

#define SPLITMIX_SEED 0x00BEEFCAFEULL
#define CANONICAL_N 1024
#define CANONICAL_CHECKSUM 1388262917130611548ULL

static inline uint64_t splitmix64_next(uint64_t *state) {
    uint64_t z;
    *state += 0x9E3779B97F4A7C15ULL;
    z = *state;
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
    return z ^ (z >> 31);
}

#endif
