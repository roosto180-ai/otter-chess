import test from 'node:test';
import assert from 'node:assert/strict';
import { Chess } from 'chess.js';
import { MatchClock, customTimeControl } from '../lib/play/match-clock.ts';
import { continuationPosition } from '../lib/play/continuation.ts';

test('elapsed time includes background suspension and never goes negative', () => {
  const c = new MatchClock(); c.start(10, 2, 'player', 1000);
  assert.equal(c.settle(4500), null); assert.equal(c.player, 6.5);
  assert.equal(c.settle(50000), 'player'); assert.equal(c.player, 0);
  assert.equal(c.settle(60000), null); assert.equal(c.otter, 10);
});
test('switching turns charges the mover and adds increment exactly once', () => {
  const c = new MatchClock(); c.start(60, 3, 'player', 0);
  assert.equal(c.move('otter', 1250), null); assert.equal(c.player, 61.75);
  c.move('player', 2250); assert.equal(c.otter, 62); c.settle(2500); assert.equal(c.player, 61.5);
});
test('a move at/after deadline is rejected without awarding increment', () => {
  const c = new MatchClock(); c.start(1, 10, 'otter', 0);
  assert.equal(c.move('player', 1000), 'otter'); assert.equal(c.otter, 0); assert.equal(c.side, 'otter');
});
test('edit settles elapsed time and preserves the inactive clock', () => {
  const c = new MatchClock(); c.start(60, 0, 'otter', 0);
  c.edit('player', 300, 5000); assert.equal(c.player, 300); assert.equal(c.otter, 55);
  c.settle(6000); assert.equal(c.otter, 54);
});
test('editing an already expired clock does not silently resume a finished game', () => {
  const c = new MatchClock(); c.start(1, 0, 'player', 0);
  assert.equal(c.edit('player', 300, 2000), 'player'); assert.equal(c.player, 300); assert.equal(c.running, false);
  c.settle(100000); assert.equal(c.player, 300);
});
test('analysis can continue at zero with fixed clocks and no increments', () => {
  const c = new MatchClock(); c.start(1, 5, 'player', 0); c.settle(1000);
  c.move('otter', 2000, true); assert.equal(c.player, 0); assert.equal(c.otter, 1); assert.equal(c.side, 'otter');
});
test('reject invalid edits and custom formats; accept fractional custom minutes', () => {
  const c = new MatchClock();
  for (const value of [-1, NaN, Infinity, 86401]) assert.throws(() => c.edit('player', value, 0));
  assert.equal(customTimeControl(7.5, 4), '450+4');
  for (const [m,i] of [[0,0],[1441,0],[5,-1],[5,1.5],[NaN,0]]) assert.throws(() => customTimeControl(m,i));
});
test('resignation/flag continuation preserves FEN, history, en passant and original result', () => {
  const c = new Chess(); for (const m of ['e4','a6','e5','d5']) c.move(m); c.header('Result','0-1');
  const pgn = c.pgn(); const {game,undone} = continuationPosition(c);
  assert.equal(undone,false); assert.equal(game.fen(),c.fen()); assert.deepEqual(game.history(),c.history());
  assert.equal(c.pgn(),pgn); assert.equal(game.header().Result,'*'); assert.ok(game.moves().includes('exd6'));
});
test('checkmate branches explicitly one ply earlier without mutating the archived game', () => {
  const c = new Chess(); ['f3','e5','g4','Qh4#'].forEach(m=>c.move(m));
  const final = c.pgn(); const {game,undone}=continuationPosition(c);
  assert.equal(undone,true); assert.equal(c.pgn(),final); assert.equal(c.isCheckmate(),true);
  assert.deepEqual(game.history(),['f3','e5','g4']); assert.equal(game.isCheckmate(),false);
  game.move('Nc6'); assert.deepEqual(game.history(),['f3','e5','g4','Nc6']);
});
test('repetition draw keeps full history and permits a different legal continuation', () => {
  const c = new Chess(); ['Nf3','Nf6','Ng1','Ng8','Nf3','Nf6','Ng1','Ng8'].forEach(m=>c.move(m));
  assert.equal(c.isThreefoldRepetition(),true); const {game,undone}=continuationPosition(c);
  assert.equal(undone,false); assert.deepEqual(game.history(),c.history()); game.move('e4'); assert.equal(game.history().length,9);
});
test('stalemate with a recorded preceding move can branch; bare terminal FEN cannot invent history', () => {
  const c = new Chess('7k/5K2/8/6Q1/8/8/8/8 w - - 0 1'); c.move('Qg6');
  assert.equal(c.isStalemate(),true);
  const {game,undone}=continuationPosition(c);
  assert.equal(undone,true); assert.equal(game.isStalemate(),false); assert.equal(game.history().length,0);
  // Use a known stalemate via Qg6 from g5 with black king h8 and white king f7.
  const terminal = new Chess('7k/5K2/6Q1/8/8/8/8/8 b - - 0 1');
  assert.equal(terminal.isStalemate(),true); assert.throws(()=>continuationPosition(terminal));
});
test('50-move draw preserves counters and castling rights rather than rebuilding from a fresh board', () => {
  const c = new Chess('r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 100 51');
  assert.equal(c.isDrawByFiftyMoves(),true); const {game}=continuationPosition(c);
  assert.equal(game.fen(),c.fen()); assert.ok(game.moves().includes('O-O'));
});

test('a mated human branches at their last decision, so Otter cannot simply replay its mate', () => {
  const c=new Chess(); ['f3','e5','g4','Qh4#'].forEach(m=>c.move(m));
  const {game}=continuationPosition(c,'w'); assert.equal(game.turn(),'w'); assert.deepEqual(game.history(),['f3','e5']);
});

test('insufficient-material draw can continue legal analysis without changing the position', () => {
  const c=new Chess('4k3/8/8/8/8/8/8/4K3 w - - 0 1'); assert.equal(c.isInsufficientMaterial(),true);
  const {game,undone}=continuationPosition(c,'w'); assert.equal(undone,false); assert.equal(game.fen(),c.fen()); game.move('Kd2'); assert.equal(game.history().length,1);
});
