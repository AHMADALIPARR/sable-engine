/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Copyright (C) 2026 SnapKitty Collective */
#include "jsoncanon.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void jb_init(jbuf *b) { b->cap = 4096; b->len = 0; b->p = malloc(b->cap); b->p[0] = 0; }
void jb_free(jbuf *b) { free(b->p); b->p = 0; b->len = b->cap = 0; }

static void jb_reserve(jbuf *b, size_t n) {
    while (b->len + n + 1 > b->cap) { b->cap *= 2; b->p = realloc(b->p, b->cap); }
}

void jb_raw(jbuf *b, const char *s) {
    size_t n = strlen(s);
    jb_reserve(b, n);
    memcpy(b->p + b->len, s, n);
    b->len += n; b->p[b->len] = 0;
}

void jb_str(jbuf *b, const char *s) {
    /* ensure_ascii=False: UTF-8 passes through raw; escape ", \, controls */
    jb_raw(b, "\"");
    for (const unsigned char *p = (const unsigned char *)s; *p; p++) {
        if (*p == '"') jb_raw(b, "\\\"");
        else if (*p == '\\') jb_raw(b, "\\\\");
        else if (*p < 0x20) { char e[8]; snprintf(e, sizeof e, "\\u%04x", *p); jb_raw(b, e); }
        else { char c[2] = {(char)*p, 0}; jb_raw(b, c); }
    }
    jb_raw(b, "\"");
}

void jb_int(jbuf *b, long long v) { char t[32]; snprintf(t, sizeof t, "%lld", v); jb_raw(b, t); }
void jb_uint(jbuf *b, unsigned long long v) { char t[32]; snprintf(t, sizeof t, "%llu", v); jb_raw(b, t); }
void jb_bool(jbuf *b, int v) { jb_raw(b, v ? "true" : "false"); }
void jb_null(jbuf *b) { jb_raw(b, "null"); }

void jb_float(jbuf *b, double x) {
    char tmp[64], fix[64];
    int prec;
    /* Fixed notation first (CPython repr uses it for our whole domain). */
    for (prec = 0; prec <= 17; prec++) {
        snprintf(fix, sizeof fix, "%.*f", prec, x);
        /* strip trailing zeros, keep at least ".0" */
        char *dot = strchr(fix, '.');
        if (dot) {
            char *end = fix + strlen(fix) - 1;
            while (end > dot && *end == '0') *end-- = 0;
            if (end == dot) { end[1] = '0'; end[2] = 0; }
        } else {
            strcat(fix, ".0"); /* "%.0f" emits no dot; Python keeps ".0" */
        }
        if (strtod(fix, NULL) == x) { jb_raw(b, fix); return; }
    }
    /* Fallback: shortest %g that round-trips (safety net, not our domain). */
    for (prec = 1; prec <= 17; prec++) {
        snprintf(tmp, sizeof tmp, "%.*g", prec, x);
        if (strtod(tmp, NULL) == x) break;
    }
    if (!strpbrk(tmp, ".eEnN")) {
        size_t L = strlen(tmp);
        tmp[L] = '.'; tmp[L+1] = '0'; tmp[L+2] = 0;
    }
    jb_raw(b, tmp);
}
