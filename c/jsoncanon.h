/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Copyright (C) 2026 SnapKitty Collective */
/* Canonical JSON builder mirroring CPython:
   json.dumps(obj, sort_keys=True, separators=(",",":"), ensure_ascii=False).
   Key order is hardcoded in sorted order (documented per call site).
   j_float reproduces CPython float repr for our domain (short decimals):
   fixed notation, stripped trailing zeros, integral floats keep ".0". */
#ifndef SABLE_JSONCANON_H
#define SABLE_JSONCANON_H

#include <stddef.h>

typedef struct { char *p; size_t len, cap; } jbuf;

void jb_init(jbuf *b);
void jb_free(jbuf *b);
void jb_raw(jbuf *b, const char *s);          /* append literal */
void jb_str(jbuf *b, const char *s);          /* quoted + escaped string */
void jb_int(jbuf *b, long long v);
void jb_uint(jbuf *b, unsigned long long v);
void jb_bool(jbuf *b, int v);
void jb_null(jbuf *b);
void jb_float(jbuf *b, double x);             /* CPython-repr compatible */

#endif
