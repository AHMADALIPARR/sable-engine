/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Copyright (C) 2026 SnapKitty Collective */
/* Self-contained SHA-256 (FIPS 180-4). Public-domain-style implementation,
   written here from the spec so the C stack has no crypto dependency. */
#ifndef SABLE_SHA256_H
#define SABLE_SHA256_H

#include <stddef.h>
#include <stdint.h>

typedef struct {
    uint32_t h[8];
    uint64_t len;
    uint8_t buf[64];
    size_t buflen;
} sha256_ctx;

void sha256_init(sha256_ctx *c);
void sha256_update(sha256_ctx *c, const uint8_t *data, size_t len);
void sha256_final(sha256_ctx *c, uint8_t out[32]);
/* One-shot: hex digest (64 chars + NUL) of data. */
void sha256_hex(const uint8_t *data, size_t len, char out[65]);

#endif
