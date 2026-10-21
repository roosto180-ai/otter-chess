# Changes and licensing

Independent adaptation, 21 October 2026. Copyright (c) 2026 contributors to the Otter self-hosted adaptation.

The original repository's MIT grant and copyright are preserved in LICENSE. Otter model weights remain under their original MIT grant. New web adaptation code is licensed under GNU GPL version 3 or later (COPYING; docs/LICENSE), in keeping with redistribution of the combined Chessground-based application. This does not remove the original MIT grants.

Changes: synchronous elapsed-time clock and increments; editable clocks, custom controls, explicit continuation analysis; preserved final PGN and position; cancellation of stale delayed AI moves; pinned self-hosted assets with SHA-256 checks; source/license downloads; static preview server and Pages workflow tests. Next.js and its build dependencies were updated without changing Otter model/ONNX runtime versions.

Third-party source distributions and license notices are served under docs/public/sources and docs/public/licenses. The application source download omits model/runtime binaries; docs/scripts/prepare-assets.mjs restores them from immutable/versioned URLs with recorded hashes. Chessground and Stockfish corresponding sources, original build scripts, and GPL notices accompany the distribution.

22 October 2026: continued human-move policy training from the official safetensors, retaining Otter's architecture and joint policy/auxiliary/value objectives. Added stratified 3+0 data, rapid replay, high-rating human blitz examples, game-disjoint validation/test splits, full-Elo checkpoint selection, and a paired policy benchmark. Corrected pre-move clock inputs and white auxiliary-target board snapshots in training. The trained model is explicitly experimental and optional via `?model=trained`; the unchanged original stays the default. Model caches and pinned checksums are isolated, PGNs identify the selected model, and inference functions/worker behavior are retained. No separate learned delay model is included. See FINETUNING-AR.md and the published training report for measured results and limitations.
