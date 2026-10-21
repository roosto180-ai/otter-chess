import manifest from '../../assets-manifest.json' with { type: 'json' };

export function modelAssetForSearch(search: string) {
  const trained = new URLSearchParams(search).get('model') === 'trained';
  const path = trained ? 'model_blitz_fp16.onnx' : 'model_fp16.onnx';
  const asset = manifest.assets.find(asset => asset.path === path);
  if (!asset) throw new Error(`Missing pinned model asset: ${path}`);
  return {
    ...asset,
    id: trained ? 'trained' : 'original',
    label: trained ? 'Otter المتدرّب على 3+0 — تجريبي' : 'Otter الأصلي',
    cacheKey: trained ? `otter-trained-fp16-${asset.sha256.slice(0, 12)}-v1` : 'otter-selfhost-fp16-d9067faf-v1',
  };
}

// Called only from browser effects/actions. Variant links perform a full navigation,
// so the model is fixed for the entire session and cannot change during a match.
export function activeModelAsset() {
  return modelAssetForSearch(typeof window === 'undefined' ? '' : window.location.search);
}
