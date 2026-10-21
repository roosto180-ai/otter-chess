"""Build game-disjoint, Elo-stratified 3+0 and rapid replay data (Lichess CC0)."""
import argparse, collections, hashlib, io, json, random, urllib.request
from pathlib import Path
import chess.pgn
import pyarrow as pa
import pyarrow.parquet as pq
import zstandard

def bucket(e):
    return 0 if e < 1100 else 10 if e >= 2000 else 1 + (e-1100)//100

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--out', required=True)
    p.add_argument('--quota', type=int, default=600, help='Games per average-Elo bucket per group')
    p.add_argument('--month', default='2025-01')
    a=p.parse_args(); root=Path(a.out); root.mkdir(parents=True,exist_ok=True)
    if a.quota<=0: raise ValueError('quota must be positive')
    if any(root.iterdir()): raise RuntimeError('Choose an empty output directory; do not mix dataset generations')
    url=f'https://database.lichess.org/standard/lichess_db_standard_rated_{a.month}.pgn.zst'
    counts=collections.Counter(); rows=[]; seen=set(); scanned=0
    class Filter(chess.pgn.GameBuilder):
        def end_headers(self):
            h=self.game.headers; tc=h.get('TimeControl','')
            group='blitz' if tc=='180+0' and h.get('Event')=='Rated Blitz game' else 'replay' if h.get('Event')=='Rated Rapid game' else None
            try: b=bucket((int(h['WhiteElo'])+int(h['BlackElo']))//2)
            except (KeyError,ValueError): return chess.pgn.SKIP
            if group is None or counts[group,b]>=a.quota: return chess.pgn.SKIP
    req=urllib.request.Request(url,headers={'User-Agent':'Otter-finetune/1.0'})
    with urllib.request.urlopen(req,timeout=120) as response:
        stream=io.TextIOWrapper(zstandard.ZstdDecompressor().stream_reader(response),encoding='utf-8')
        while min((counts[g,b] for g in ('blitz','replay') for b in range(11)),default=0)<a.quota:
            game=chess.pgn.read_game(stream,Visitor=Filter)
            if game is None: break
            scanned+=1; h=game.headers; tc=h.get('TimeControl','')
            group='blitz' if tc=='180+0' and h.get('Event')=='Rated Blitz game' else 'replay' if h.get('Event')=='Rated Rapid game' else None
            if group is None or h.get('Variant','Standard')!='Standard' or h.get('SetUp') or game.errors: continue
            if h.get('WhiteTitle')=='BOT' or h.get('BlackTitle')=='BOT': continue
            try: we,be=int(h['WhiteElo']),int(h['BlackElo']); base,inc=map(int,tc.split('+'))
            except (KeyError,ValueError): continue
            if min(we,be)<600 or max(we,be)>3200 or h.get('Result') not in ('1-0','0-1','1/2-1/2'): continue
            b=bucket((we+be)//2); site=h.get('Site','')
            if counts[group,b]>=a.quota or not site or site in seen: continue
            board=game.board(); sans=[]; clocks=[]; own=[float(base),float(base)]
            valid=True
            for node in game.mainline():
                clock=node.clock()
                if clock is None: valid=False; break
                side=0 if board.turn else 1
                # Input is the clock known BEFORE the labelled move, avoiding target leakage.
                s=max(0,int(own[side])); clocks.append(f'{s//3600}:{s//60%60:02}:{s%60:02}')
                sans.append(board.san(node.move)); board.push(node.move); own[side]=clock
            if not valid or len(sans)<30: continue
            counts[group,b]+=1; seen.add(site)
            split_hash=int(hashlib.sha256(site.encode()).hexdigest()[:8],16)%10
            split='test' if split_hash==0 else 'validation' if split_hash==1 else 'train'
            avg=(we+be)//2; band=0 if avg<1000 else min(8,1+(avg-1000)//200)
            rows.append(dict(month=split,elo_band=band,result=h['Result'],white_elo=we,black_elo=be,
                             time_control=tc,move_clocks='|'.join(clocks),moves_san=' '.join(sans),
                             source_id=site,group=group,elo_bucket=b))
            if len(rows)%250==0: print(json.dumps({'games':len(rows),'scanned':scanned,'minimum_bucket':min(counts[g,k] for g in ('blitz','replay') for k in range(11))}),flush=True)
    for split in ('train','validation','test'):
        for band in range(9):
            subset=[r for r in rows if r['month']==split and r['elo_band']==band]
            if subset:
                path=root/f'month={split}'/f'elo_band={band}'; path.mkdir(parents=True,exist_ok=True)
                random.Random(20261022+band).shuffle(subset)
                for start in range(0,len(subset),8):
                    pq.write_table(pa.Table.from_pylist(subset[start:start+8]),path/f'part-{start//8:06}.parquet')
    report={'url':url,'license':'CC0','scanned':scanned,'games':len(rows),'quota':a.quota,
            'counts':{f'{g}:{b}':counts[g,b] for g in ('blitz','replay') for b in range(11)},
            'split_counts':dict(collections.Counter(r['month'] for r in rows)),
            'limitations':['Prefix sample, not population-random','Game-disjoint; players may overlap','Rating strata use average game Elo; evaluate active-player buckets separately']}
    (root/'provenance.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    if any(counts[g,b]<a.quota for g in ('blitz','replay') for b in range(11)): raise RuntimeError('Incomplete Elo coverage')

if __name__=='__main__': main()
