/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Copyright (C) 2026 SnapKitty Collective */
/* SABLE-C: the fast stack. Sparse SUBLEQ execution over the Goldilocks
   field, resonance-gated by the APL machine's sovereign vector, with an
   exact energy ledger and WORM sealing byte-compatible with aplre's log.
   The Python package (sable/) is the reference oracle: it defines truth.
   This binary is what runs. Cross-checked bit-for-bit (tests/test_crosscheck.sh).
   Exit codes: 0 completed, 2 invalid-gate, 3 checksum-failed, 4 budget-exhausted. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/time.h>
#include <time.h>

#include "field.h"
#include "splitmix.h"
#include "sha256.h"
#include "jsoncanon.h"

/* Resonance table: vendored from aplre DEFAULT_RESONANCE (documented). */
static const char *GLYPH[6] = {"\xe2\x8a\x99", "\xe2\x96\xa6", "\xe2\x97\x8b",
                               "\xe2\x97\x87", "\xe2\x96\xb3", "\xe2\xac\xa1"};
static const char *CNAME[6] = {"origin", "ledger", "oracle", "policy", "consensus", "mesh"};

/* Energy model: 1 unit = one SUBLEQ predicate evaluation. Modeled, not silicon. */
#define E_PRED 1.0
#define E_EXEC 8.0
#define E_GATED_SKIP 0.5
#define E_UNTAKEN 0.25
#define E_SEAL 4.0

typedef struct {
    long n; double res_threshold; double budget;
    int truths[6]; double res[6];
    uint64_t threshold; int threshold_half;
    uint16_t *words; long nwords;
    const char *entropy_provenance;
    const char *seal_log; const char *name;
} cfg_t;

static double ledger_spent(double sp[4]) { return sp[0] + sp[1] + sp[2] + sp[3]; }
/* sp: [pred, exec, skip, seal] */
/* returns 0 ok, 1 exhausted */
static int charge(double sp[4], double budget, int idx, double amount) {
    if (ledger_spent(sp) + amount > budget) return 1;
    sp[idx] += amount;
    return 0;
}

static void usage(const char *p) {
    fprintf(stderr,
        "usage: %s --entropy-hex <hex> [options]\n"
        "  --n <int>                 lanes (default 1024)\n"
        "  --threshold half|<u64>    SUBLEQ comparison point (default half)\n"
        "  --resonance <float>       gate threshold (default 0.75)\n"
        "  --budget <float>          energy budget (default 20000)\n"
        "  --truths a,b,c,d,e,f      AND-fold veto vector (default all 1)\n"
        "  --resonances r0..r5       override resonance table\n"
        "  --entropy-provenance <s>  e.g. quantum | fallback-csprng\n"
        "  --seal-log <path>         (default seals.jsonl)\n"
        "  --name <str>              pass name\n"
        "  --selftest                run built-in checks\n", p);
}

static int parse_truths(const char *s, int out[6]) {
    for (int i = 0; i < 6; i++) {
        char *end; long v = strtol(s, &end, 10);
        if (v != 0 && v != 1) return -1;
        out[i] = (int)v;
        if (i < 5) { if (*end != ',') return -1; s = end + 1; }
    }
    return 0;
}

static int parse_res(const char *s, double out[6]) {
    for (int i = 0; i < 6; i++) {
        char *end; double v = strtod(s, &end);
        out[i] = v;
        if (i < 5) { if (*end != ',') return -1; s = end + 1; }
    }
    return 0;
}

/* Fisher-Yates over order[0..n-1] driven by 16-bit words (mirrors anu.quantum_shuffle). */
static void quantum_shuffle(long *order, long n, uint16_t *w, long nw) {
    long e = 0;
    for (long i = n - 1; i >= 1; i--) {
        long j = w[e % nw] % (i + 1);
        e++;
        long t = order[i]; order[i] = order[j]; order[j] = t;
    }
}

typedef struct { long lane; double res; long pos; } slot_t;
static int slot_cmp(const void *A, const void *B) {
    const slot_t *a = A, *b = B;
    if (a->res > b->res) return -1;
    if (a->res < b->res) return 1;
    return (a->pos > b->pos) - (a->pos < b->pos);
}

/* Read the seal of the last log line ("prev" link). Returns 1 if found. */
static int read_prev_seal(const char *path, char out[65]) {
    FILE *f = fopen(path, "r");
    if (!f) return 0;
    char line[1 << 20], last[1 << 20];
    last[0] = 0;
    while (fgets(line, sizeof line, f)) {
        char *p = line + strlen(line);
        while (p > line && (p[-1] == '\n' || p[-1] == '\r')) *--p = 0;
        if (*line) strcpy(last, line);
    }
    fclose(f);
    if (!*last) return 0;
    char *m = strstr(last, "\"seal\":\"");
    if (!m || strlen(m + 8) < 64) return 0;
    memcpy(out, m + 8, 64); out[64] = 0;
    return 1;
}

static int cmd_verify(const char *path) {
    FILE *f = fopen(path, "r");
    if (!f) { printf("chain valid: False - cannot open %s\n", path); return 1; }
    char line[1 << 20];
    char prev[65] = {0};
    long n = 0;
    int ok = 1;
    const char *fail = "";
    while (ok && fgets(line, sizeof line, f)) {
        char *p = line + strlen(line);
        while (p > line && (p[-1] == '\n' || p[-1] == '\r')) *--p = 0;
        if (!*line) continue;
        char *ms = strstr(line, "\"seal\":\"");
        char *mp = strstr(line, "\"prev\":");
        char *mpl = strstr(line, "\"payload\":");
        if (!ms || !mp || !mpl || strlen(ms + 8) < 64) { ok = 0; fail = "malformed entry"; break; }
        char seal[65]; memcpy(seal, ms + 8, 64); seal[64] = 0;
        /* prev link */
        char *pv = mp + 7;
        while (*pv == ' ') pv++;
        char want_prev[65] = {0};
        if (!strncmp(pv, "null", 4)) want_prev[0] = 0;
        else if (*pv == '"' && strlen(pv) > 65) { memcpy(want_prev, pv + 1, 64); want_prev[64] = 0; }
        else { ok = 0; fail = "malformed prev"; break; }
        if (n == 0 ? want_prev[0] != 0 : strcmp(want_prev, prev)) {
            ok = 0; fail = "prev link broken"; break;
        }
        /* payload bytes: brace-match from the '{' after "payload": */
        char *ps = strchr(mpl + 10, '{');
        if (!ps) { ok = 0; fail = "no payload"; break; }
        char *q = ps; int depth = 0, instr = 0, esc = 0;
        char *pe = NULL;
        for (; *q; q++) {
            char chh = *q;
            if (instr) {
                if (esc) esc = 0;
                else if (chh == '\\') esc = 1;
                else if (chh == '"') instr = 0;
            } else {
                if (chh == '"') instr = 1;
                else if (chh == '{') depth++;
                else if (chh == '}') { depth--; if (depth == 0) { pe = q; break; } }
            }
        }
        if (!pe) { ok = 0; fail = "payload brace mismatch"; break; }
        char d[65];
        sha256_hex((const uint8_t *)ps, (size_t)(pe - ps + 1), d);
        if (strcmp(d, seal)) { ok = 0; fail = "digest mismatch (tampered?)"; break; }
        strcpy(prev, seal);
        n++;
    }
    fclose(f);
    if (ok) printf("chain valid: True - %ld seal(s) verified, chain intact\n", n);
    else printf("chain valid: False - %s\n", fail);
    return ok ? 0 : 1;
}

static int selftest(void) {
    int fails = 0;
#define CK(cond, msg) do { if (!(cond)) { printf("FAIL %s\n", msg); fails++; } } while (0)
    CK(gf_add(P_U64 - 1, 1) == 0, "gf_add carry");
    CK(gf_sub(0, 1) == P_U64 - 1, "gf_sub wrap");
    CK(gf_mul(2, P_U64 - 1) == P_U64 - 2, "gf_mul");
    CK(to_signed(0xFFFFFFFFFFFFFFFFULL) == -1, "to_signed");
    { uint64_t st = SPLITMIX_SEED, acc = 0;
      for (int i = 0; i < CANONICAL_N; i++) acc = gf_add(acc, splitmix64_next(&st));
      CK(acc == CANONICAL_CHECKSUM, "canonical checksum"); }
    { char h[65]; sha256_hex((const uint8_t *)"abc", 3, h);
      CK(!strcmp(h, "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"), "sha256"); }
    { jbuf b; jb_init(&b);
      jb_float(&b, 0.9); CK(!strcmp(b.p, "0.9"), "float 0.9");
      b.len = 0; jb_float(&b, 1.0); CK(!strcmp(b.p, "1.0"), "float 1.0");
      b.len = 0; jb_float(&b, 20000.0); CK(!strcmp(b.p, "20000.0"), "float 20000.0");
      b.len = 0; jb_float(&b, 4606.5); CK(!strcmp(b.p, "4606.5"), "float 4606.5");
      b.len = 0; jb_float(&b, 0.85); CK(!strcmp(b.p, "0.85"), "float 0.85");
      b.len = 0; jb_float(&b, 5.0); CK(!strcmp(b.p, "5.0"), "float 5.0");
      jb_free(&b); }
    printf(fails ? "SELFTEST FAILED\n" : "SELFTEST PASS\n");
    return fails ? 1 : 0;
#undef CK
}

int main(int argc, char **argv) {
    cfg_t c;
    memset(&c, 0, sizeof c);
    c.n = 1024; c.res_threshold = 0.75; c.budget = 20000.0;
    c.threshold_half = 1;
    for (int i = 0; i < 6; i++) c.truths[i] = 1;
    double defres[6] = {1.00, 0.90, 0.80, 0.70, 0.85, 0.75};
    memcpy(c.res, defres, sizeof defres);
    c.entropy_provenance = "external";
    c.seal_log = "seals.jsonl";
    c.name = "eclipse-pass-01";
    const char *hex = NULL;

    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--selftest")) return selftest();
        else if (!strcmp(argv[i], "verify")) {
            const char *p = "seals.jsonl";
            for (int j = i + 1; j + 1 < argc; j++)
                if (!strcmp(argv[j], "--seal-log")) p = argv[j + 1];
            return cmd_verify(p);
        }
        else if (!strcmp(argv[i], "--n") && i + 1 < argc) c.n = atol(argv[++i]);
        else if (!strcmp(argv[i], "--threshold") && i + 1 < argc) {
            i++;
            if (!strcmp(argv[i], "half")) c.threshold_half = 1;
            else { c.threshold_half = 0; c.threshold = strtoull(argv[i], 0, 10); }
        }
        else if (!strcmp(argv[i], "--resonance") && i + 1 < argc) c.res_threshold = strtod(argv[++i], 0);
        else if (!strcmp(argv[i], "--budget") && i + 1 < argc) c.budget = strtod(argv[++i], 0);
        else if (!strcmp(argv[i], "--truths") && i + 1 < argc) {
            if (parse_truths(argv[++i], c.truths)) { usage(argv[0]); return 1; }
        }
        else if (!strcmp(argv[i], "--resonances") && i + 1 < argc) {
            if (parse_res(argv[++i], c.res)) { usage(argv[0]); return 1; }
        }
        else if (!strcmp(argv[i], "--entropy-hex") && i + 1 < argc) hex = argv[++i];
        else if (!strcmp(argv[i], "--entropy-provenance") && i + 1 < argc) c.entropy_provenance = argv[++i];
        else if (!strcmp(argv[i], "--seal-log") && i + 1 < argc) c.seal_log = argv[++i];
        else if (!strcmp(argv[i], "--name") && i + 1 < argc) c.name = argv[++i];
        else { usage(argv[0]); return 1; }
    }
    if (!hex || strlen(hex) % 4 != 0 || !*hex) { usage(argv[0]); return 1; }
    if (c.threshold_half) c.threshold = (uint64_t)(P128 / 2);

    /* 1. The APL gate: AND-fold veto. */
    int valid = 1;
    for (int i = 0; i < 6; i++) valid &= c.truths[i];
    printf("pass:      %s\n", c.name);
    if (!valid) {
        printf("status:    invalid-gate\n"
               "gate:      INVALID (veto)\n"
               "seal:      (withheld)\n");
        return 2;
    }

    /* 2. Verify-before-record: canonical checksum over the n=1024 stream. */
    { uint64_t st = SPLITMIX_SEED, acc = 0;
      for (int i = 0; i < CANONICAL_N; i++) acc = gf_add(acc, splitmix64_next(&st));
      if (acc != CANONICAL_CHECKSUM) {
          printf("status:    checksum-failed\nseal:      (withheld)\n");
          return 3;
      } }

    /* 3. Entropy words from hex. */
    long hn = strlen(hex) / 4;
    c.words = malloc(hn * sizeof(uint16_t)); c.nwords = hn;
    for (long i = 0; i < hn; i++) {
        unsigned v; sscanf(hex + 4 * i, "%4x", &v);
        c.words[i] = (uint16_t)v;
    }
    char nonce[17];
    { unsigned long long v = 0;
      for (long i = 0; i < 4 && i < hn; i++) v = ((v << 16) | c.words[i]) & 0xFFFFFFFFFFFFFFFFULL;
      snprintf(nonce, sizeof nonce, "%016llx", v); }

    /* 4. Lane order: quantum shuffle, then highest-resonance-first (stable). */
    long n = c.n;
    long *order = malloc(n * sizeof(long));
    for (long i = 0; i < n; i++) order[i] = i;
    quantum_shuffle(order, n, c.words, c.nwords);
    slot_t *slots = malloc(n * sizeof(slot_t));
    for (long i = 0; i < n; i++)
        slots[i] = (slot_t){order[i], c.res[order[i] % 6], i};
    qsort(slots, n, sizeof(slot_t), slot_cmp);

    /* 5. The sparse pass. */
    uint64_t *xs = malloc(n * sizeof(uint64_t));
    { uint64_t st = SPLITMIX_SEED;
      for (long i = 0; i < n; i++) xs[i] = splitmix64_next(&st); }
    double sp[4] = {0, 0, 0, 0};
    uint64_t total = 0;
    long taken = 0, executed = 0, gated_skip = 0, untaken = 0;
    int exhausted = 0;
    for (long k = 0; k < n && !exhausted; k++) {
        long i = slots[k].lane;
        if (charge(sp, c.budget, 0, E_PRED)) { exhausted = 1; break; }
        uint64_t d = gf_sub(xs[i], c.threshold);
        if (to_signed(d) > 0) {
            if (charge(sp, c.budget, 2, E_UNTAKEN)) { exhausted = 1; break; }
            untaken++; continue;
        }
        taken++;
        if (c.res[i % 6] >= c.res_threshold) {
            total = gf_add(total, xs[i]);
            if (charge(sp, c.budget, 1, E_EXEC)) { exhausted = 1; break; }
            executed++;
        } else {
            if (charge(sp, c.budget, 2, E_GATED_SKIP)) { exhausted = 1; break; }
            gated_skip++;
        }
    }
    if (exhausted) {
        printf("status:    budget-exhausted\n"
               "gate:      VALID\n"
               "checksum:  OK\n"
               "entropy:   %s  nonce=%s\n"
               "energy:    spent=%.1f / budget=%.1f\n"
               "seal:      (withheld)\n",
               c.entropy_provenance, nonce, ledger_spent(sp), c.budget);
        return 4;
    }

    /* 6. Seal: canonical payload -> sha256 -> append {seal,prev,payload}. */
    if (charge(sp, c.budget, 3, E_SEAL)) {
        printf("status:    budget-exhausted\nseal:      (withheld)\n");
        return 4;
    }
    double res_total = 0;
    for (int i = 0; i < 6; i++) res_total += c.res[i];

    struct timeval tv; gettimeofday(&tv, NULL);
    struct tm *tm = gmtime(&tv.tv_sec);
    char ts[40];
    snprintf(ts, sizeof ts, "%04d-%02d-%02dT%02d:%02d:%02d.%06ld+00:00",
             tm->tm_year + 1900, tm->tm_mon + 1, tm->tm_mday,
             tm->tm_hour, tm->tm_min, tm->tm_sec, (long)tv.tv_usec);

    jbuf p; jb_init(&p);
    jb_raw(&p, "{\"and_fold\":"); jb_bool(&p, valid);
    jb_raw(&p, ",\"components\":[");
    for (int i = 0; i < 6; i++) {
        if (i) jb_raw(&p, ",");
        jb_raw(&p, "{\"gate_open\":"); jb_bool(&p, c.res[i] >= c.res_threshold);
        jb_raw(&p, ",\"glyph\":"); jb_str(&p, GLYPH[i]);
        jb_raw(&p, ",\"name\":"); jb_str(&p, CNAME[i]);
        jb_raw(&p, ",\"resonance\":"); jb_float(&p, c.res[i]);
        jb_raw(&p, ",\"truth\":"); jb_int(&p, c.truths[i]);
        jb_raw(&p, "}");
    }
    jb_raw(&p, "],\"meta\":\"sable-pass\"");
    jb_raw(&p, ",\"omega_truth\":"); jb_bool(&p, valid);
    jb_raw(&p, ",\"resonance_total\":"); jb_float(&p, res_total);
    jb_raw(&p, ",\"sable_receipt\":{");
    jb_raw(&p, "\"anu_nonce\":"); jb_str(&p, nonce);
    jb_raw(&p, ",\"anu_provenance\":"); jb_str(&p, c.entropy_provenance);
    jb_raw(&p, ",\"energy\":{");
    jb_raw(&p, "\"budget\":"); jb_float(&p, c.budget);
    jb_raw(&p, ",\"remaining\":"); jb_float(&p, c.budget - ledger_spent(sp));
    jb_raw(&p, ",\"spent_exec\":"); jb_float(&p, sp[1]);
    jb_raw(&p, ",\"spent_predicate\":"); jb_float(&p, sp[0]);
    jb_raw(&p, ",\"spent_seal\":"); jb_float(&p, sp[3]);
    jb_raw(&p, ",\"spent_skip\":"); jb_float(&p, sp[2]);
    jb_raw(&p, ",\"spent_total\":"); jb_float(&p, ledger_spent(sp));
    jb_raw(&p, "}");
    jb_raw(&p, ",\"executed\":"); jb_int(&p, executed);
    jb_raw(&p, ",\"n\":"); jb_int(&p, n);
    jb_raw(&p, ",\"pass\":"); jb_str(&p, c.name);
    jb_raw(&p, ",\"pred_taken\":"); jb_int(&p, taken);
    jb_raw(&p, ",\"result\":"); jb_uint(&p, total);
    jb_raw(&p, ",\"status\":\"completed\"");
    jb_raw(&p, "},\"timestamp\":"); jb_str(&p, ts);
    jb_raw(&p, "}");

    char digest[65];
    sha256_hex((const uint8_t *)p.p, p.len, digest);
    char prev[65]; int has_prev = read_prev_seal(c.seal_log, prev);
    jbuf e; jb_init(&e);
    jb_raw(&e, "{\"seal\":"); jb_str(&e, digest);
    jb_raw(&e, ",\"prev\":");
    if (has_prev) jb_str(&e, prev); else jb_null(&e);
    jb_raw(&e, ",\"payload\":"); jb_raw(&e, p.p);
    jb_raw(&e, "}\n");
    FILE *f = fopen(c.seal_log, "a");
    if (!f) { fprintf(stderr, "cannot open seal log %s\n", c.seal_log); return 1; }
    fwrite(e.p, 1, e.len, f); fclose(f);

    double sparsity = 100.0 * (1.0 - (double)executed / (double)n);
    printf("status:    completed\n"
           "gate:      VALID\n"
           "checksum:  OK\n"
           "entropy:   %s  nonce=%s\n"
           "lanes:     visited=%ld taken=%ld executed=%ld gated_skip=%ld untaken=%ld\n"
           "sparsity:  %.1f%% of lanes skipped work\n"
           "result:    %llu\n"
           "energy:    spent=%.1f / budget=%.1f (pred=%.1f exec=%.1f skip=%.1f seal=%.1f)\n"
           "seal:      %s\n",
           c.entropy_provenance, nonce,
           n, taken, executed, gated_skip, untaken,
           sparsity, (unsigned long long)total,
           ledger_spent(sp), c.budget, sp[0], sp[1], sp[2], sp[3],
           digest);
    jb_free(&p); jb_free(&e);
    free(order); free(slots); free(xs); free(c.words);
    return 0;
}
