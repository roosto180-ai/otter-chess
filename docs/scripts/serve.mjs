import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../out');
const prefix = (process.env.NEXT_PUBLIC_BASE_PATH || '').replace(/\/$/,'');
const port = Number(process.env.PORT || 3000);
const types = {'.html':'text/html; charset=utf-8','.js':'text/javascript','.mjs':'text/javascript','.wasm':'application/wasm','.json':'application/json','.css':'text/css','.svg':'image/svg+xml','.png':'image/png','.ico':'image/x-icon','.onnx':'application/octet-stream','.txt':'text/plain; charset=utf-8','.webmanifest':'application/manifest+json','.zip':'application/zip'};
if (!fs.existsSync(path.join(root,'index.html'))) throw Error('Run npm run build first');
http.createServer((req,res) => {
  let url;
  try {url=decodeURIComponent(new URL(req.url,'http://localhost').pathname);} catch {res.writeHead(400).end();return;}
  if(prefix && url=== '/') {res.writeHead(302,{Location:prefix+'/play/'}).end();return;}
  if(prefix && !url.startsWith(prefix+'/')) {res.writeHead(404).end();return;}
  let file=path.resolve(root,'.'+url.slice(prefix.length));
  if(file !== root && !file.startsWith(root+path.sep)){res.writeHead(403).end();return;}
  try {if(fs.statSync(file).isDirectory()) file=path.join(file,'index.html');const stat=fs.statSync(file);
    res.writeHead(200,{'Content-Type':types[path.extname(file)]||'application/octet-stream','Content-Length':stat.size});
    if(req.method==='HEAD')res.end();else fs.createReadStream(file).pipe(res);
  }catch{res.writeHead(404).end('Not found');}
}).listen(port,'127.0.0.1',()=>console.log(`Otter: http://127.0.0.1:${port}${prefix}/play/`));
