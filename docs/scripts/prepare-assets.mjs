import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const manifest=JSON.parse(fs.readFileSync(path.join(root,'assets-manifest.json')));
for(const asset of manifest.assets){
  const file=path.join(root,'public',asset.path);
  if(!fs.existsSync(file)){
    fs.mkdirSync(path.dirname(file),{recursive:true});
    const response=await fetch(asset.url);
    if(!response.ok)throw Error(`Download failed: ${asset.path} (${response.status})`);
    fs.writeFileSync(file,Buffer.from(await response.arrayBuffer()));
  }
  const hash=crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
  if(hash!==asset.sha256)throw Error(`Checksum mismatch: ${asset.path}. Remove this file and run prepare-assets again.`);
}
console.log(`Verified ${manifest.assets.length} pinned assets.`);
