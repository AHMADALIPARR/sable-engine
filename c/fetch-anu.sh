#!/bin/sh
# SPDX-License-Identifier: LicenseRef-NON-AI-MPL-2.0
# Copyright (C) 2026 SnapKitty Collective
# Fetch ANU QRNG uint16 words; print "<hexwords> <provenance>".
# Quantum first (2s timeout); local /dev/urandom fallback, provenance-tagged.
# No Python: plain sh + curl + sed. Stdlib-only spirit, shell edition.
N=${1:-16}
if out=$(curl -sS --max-time 2 "https://qrng.anu.edu.au/API/jsonI.php?length=${N}&type=uint16" 2>/dev/null) \
   && echo "$out" | grep -q '"success":true'; then
    data=$(echo "$out" | sed -n 's/.*"data":\[\([^]]*\)\].*/\1/p')
    hex=$(echo "$data" | tr ',' '\n' | while read -r v; do printf '%04x' "$v"; done)
    if [ -n "$hex" ]; then
        echo "$hex quantum"
        exit 0
    fi
fi
hex=$(od -A n -t u2 -N $((N * 2)) /dev/urandom | tr -s ' ' '\n' | grep -E '^[0-9]+$' \
    | while read -r v; do printf '%04x' "$v"; done)
echo "$hex fallback-csprng"
