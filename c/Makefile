# SPDX-License-Identifier: LicenseRef-NON-AI-MPL-2.0
# Copyright (C) 2026 SnapKitty Collective
CC = gcc
CFLAGS = -O3 -std=c11 -Wall -Wextra

sable: sable.c sha256.c jsoncanon.c field.h splitmix.h sha256.h jsoncanon.h
	$(CC) $(CFLAGS) -o sable sable.c sha256.c jsoncanon.c

selftest: sable
	./sable --selftest

clean:
	rm -f sable

.PHONY: selftest clean
