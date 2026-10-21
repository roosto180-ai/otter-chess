# Changes and licensing

Independent adaptation, 21 October 2026. Copyright (c) 2026 contributors to the Otter self-hosted adaptation.

The original repository's MIT grant and copyright are preserved in LICENSE. Otter model weights remain under their original MIT grant. New web adaptation code is licensed under GNU GPL version 3 or later (COPYING; docs/LICENSE), in keeping with redistribution of the combined Chessground-based application. This does not remove the original MIT grants.

Changes: synchronous elapsed-time clock and increments; editable clocks, custom controls, explicit continuation analysis; preserved final PGN and position; cancellation of stale delayed AI moves; pinned self-hosted assets with SHA-256 checks; source/license downloads; static preview server and Pages workflow tests. Next.js and its build dependencies were updated without changing Otter model/ONNX runtime versions.

Third-party source distributions and license notices are served under docs/public/sources and docs/public/licenses. The application source download omits model/runtime binaries; docs/scripts/prepare-assets.mjs restores them from immutable/versioned URLs with recorded hashes. Chessground and Stockfish corresponding sources, original build scripts, and GPL notices accompany the distribution.
