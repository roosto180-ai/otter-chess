"""Add stronger human examples to Otter's shared >=2000 Elo bucket, retaining all others."""
import argparse,collections,hashlib,io,json,random,urllib.request
from pathlib import Path
import chess.pgn,pyarrow as pa,pyarrow.parquet as pq,zstandard

def main():
    p=argparse.ArgumentParser(); p.add_argument('--base',required=True); p.add_argument('--out',required=True)
    p.add_argument('--quota',type=int,default=1200)
    p.add_argument('--rapid-quota',type=int,default=0); a=p.parse_args()
    root=Path(a.out); root.mkdir(parents=True,exist_ok=True)
    if any(root.iterdir()) or a.quota<=0: raise RuntimeError('Use an empty output directory and a positive quota')
    rows=[]
    for path in sorted(Path(a.base).rglob('*.parquet')): rows.extend(pq.ParquetFile(path).read().to_pylist())
    seen={r['source_id'] for r in rows}; counts=collections.Counter(); scanned=0
    def wanted(h):
        tc=h.get('TimeControl',''); event=h.get('Event','')
        g='blitz' if tc=='180+0' and event=='Rated Blitz game' else 'replay' if event=='Rated Rapid game' else None
        try: we,be=int(h['WhiteElo']),int(h['BlackElo'])
        except (KeyError,ValueError): return None
        if g is None or min(we,be)<2300 or (we+be)//2<2400 or max(we,be)>3200: return None
        if counts[g]>=(a.quota if g=='blitz' else a.rapid_quota): return None
        if h.get('WhiteTitle')=='BOT' or h.get('BlackTitle')=='BOT' or h.get('Site','') in seen: return None
        if h.get('SetUp') or h.get('Variant','Standard')!='Standard': return None
        return g
    class Filter(chess.pgn.GameBuilder):
        def end_headers(self):
            if wanted(self.game.headers) is None: return chess.pgn.SKIP
    url='https://database.lichess.org/standard/lichess_db_standard_rated_2025-01.pgn.zst'
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Otter-finetune/1.0'}),timeout=120) as response:
        stream=io.TextIOWrapper(zstandard.ZstdDecompressor().stream_reader(response),encoding='utf-8')
        while counts['blitz']<a.quota or counts['replay']<a.rapid_quota:
            game=chess.pgn.read_game(stream,Visitor=Filter)
            if game is None: break
            scanned+=1; h=game.headers; group=wanted(h)
            if group is None or game.errors or h.get('Result') not in ('1-0','0-1','1/2-1/2'): continue
            base,inc=map(int,h['TimeControl'].split('+')); own=[float(base)]*2; board=game.board(); sans=[]; clocks=[]; valid=True
            for node in game.mainline():
                clock=node.clock()
                if clock is None: valid=False; break
                side=0 if board.turn else 1; s=max(0,int(own[side])); clocks.append(f'{s//3600}:{s//60%60:02}:{s%60:02}')
                sans.append(board.san(node.move)); board.push(node.move); own[side]=clock
            if not valid or len(sans)<30: continue
            we,be=int(h['WhiteElo']),int(h['BlackElo']); avg=(we+be)//2; sid=h['Site']; seen.add(sid); counts[group]+=1
            token=int(hashlib.sha256(sid.encode()).hexdigest()[:8],16)%10
            split='test' if token==0 else 'validation' if token==1 else 'train'
            rows.append(dict(month=split,elo_band=min(8,1+(avg-1000)//200),result=h['Result'],white_elo=we,black_elo=be,
                time_control=h['TimeControl'],move_clocks='|'.join(clocks),moves_san=' '.join(sans),source_id=sid,group=group,elo_bucket=10))
            if sum(counts.values())%100==0: print(json.dumps({'elite_games':dict(counts),'scanned':scanned}),flush=True)
    if counts['blitz']<a.quota or counts['replay']<a.rapid_quota: raise RuntimeError('Insufficient elite data')
    for split in ('train','validation','test'):
        for band in range(9):
            subset=[r for r in rows if r['month']==split and r['elo_band']==band]; random.Random(20261022+band).shuffle(subset)
            path=root/f'month={split}'/f'elo_band={band}'
            if subset: path.mkdir(parents=True,exist_ok=True)
            for start in range(0,len(subset),8): pq.write_table(pa.Table.from_pylist(subset[start:start+8]),path/f'part-{start//8:06}.parquet')
    report={'source':url,'license':'CC0','base_games':len(rows)-sum(counts.values()),'elite_added':dict(counts),'games':len(rows),
        'elite_filter':'Both players >=2300, average >=2400, neither >3200; marked BOT accounts excluded',
        'split_counts':dict(collections.Counter(r['month'] for r in rows)),'scanned':scanned,
        'limitations':['Same-month prefix sample','Game-disjoint; players can overlap','Native >=2000 bucket remains shared']}
    (root/'provenance.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report),flush=True)

if __name__=='__main__': main()
