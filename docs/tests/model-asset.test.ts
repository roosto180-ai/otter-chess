import test from 'node:test';
import assert from 'node:assert/strict';
import { modelAssetForSearch } from '../lib/play/model-asset.ts';
import { Chess } from 'chess.js';
import { continuationPosition } from '../lib/play/continuation.ts';

test('original and trained model caches cannot supply each other’s weights', () => {
  const original = modelAssetForSearch('');
  const trained = modelAssetForSearch('?model=trained');
  assert.notEqual(original.sha256, trained.sha256);
  assert.notEqual(original.cacheKey, trained.cacheKey);
  assert.notEqual(original.path, trained.path);
  assert.equal(original.cacheKey, 'otter-selfhost-fp16-d9067faf-v1');
  assert.deepEqual(modelAssetForSearch('?model=unknown'), original);
});

test('model identity survives PGN parsing, moves and post-game continuation', () => {
  const model = modelAssetForSearch('?model=trained');
  const game = new Chess();
  game.header('OtterModel', model.id, 'OtterModelHash', model.sha256);
  game.move('e4'); game.move('e5');
  game.header('Result', '0-1');
  const clone = new Chess(); clone.loadPgn(game.pgn());
  assert.equal(clone.header().OtterModelHash, model.sha256);
  const branch = continuationPosition(clone).game;
  branch.move('Nf3');
  assert.deepEqual(branch.history(), ['e4', 'e5', 'Nf3']);
  assert.equal(branch.header().OtterModel, 'trained');
  assert.equal(branch.header().OtterModelHash, model.sha256);
  assert.equal(game.header().Result, '0-1');
  assert.equal(game.history().length, 2);
});
