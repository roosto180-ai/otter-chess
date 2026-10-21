import { Chess } from 'chess.js';

/** Clone by PGN so repetitions, halfmove counters, castling, en passant and move history survive. */
export function continuationPosition(source: Chess, playerColor?: 'w' | 'b'): { game: Chess; undone: boolean } {
  const game = new Chess();
  game.loadPgn(source.pgn());
  const undone = game.moves().length === 0;
  if (undone && !game.undo()) throw new Error('No previous legal position is available');
  if (undone && playerColor && game.turn() !== playerColor && !game.undo()) throw new Error('No earlier player decision is available');
  if (!game.moves().length) throw new Error('No legal moves are available');
  game.header('Result', '*', 'Event', 'Otter continuation analysis');
  return { game, undone };
}
