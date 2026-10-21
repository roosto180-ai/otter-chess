"""Paired opening policy benchmark. Fixed 3+0 conditioning, no real-time flagging."""
import argparse, hashlib, json, random
from pathlib import Path
import chess, chess.pgn, fastchess, pyarrow.parquet as pq, torch
from safetensors.torch import load_file
from data_loader import board_to_tensor, encode_history, legal_move_mask, load_vocab, canonicalize_move, mirror_move
from train import build_model, masked_policy_logits

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--original',required=True); p.add_argument('--candidate',required=True)
    p.add_argument('--data',required=True); p.add_argument('--out',required=True)
    p.add_argument('--pairs',type=int,default=50); p.add_argument('--device',default='cpu')
    p.add_argument('--split',choices=['validation','test'],default='test')
    p.add_argument('--exclude-pgn',default=None)
    a=p.parse_args(); torch.set_num_threads(8); device=torch.device(a.device)
    models=[]
    for file in (a.original,a.candidate):
        model=build_model(20).to(device); model.load_state_dict(load_file(file),strict=True); model.eval(); models.append(model)
    policy,history=load_vocab(); id_to_move={i:m for m,i in policy.items()}
    rows=[]
    for file in sorted(Path(a.data).glob(f'month={a.split}/elo_band=*/*.parquet')):
        rows.extend(r for r in pq.ParquetFile(file).read().to_pylist() if r['time_control']=='180+0')
    random.Random(20261022).shuffle(rows); openings=[]; seen=set()
    if a.exclude_pgn:
        with Path(a.exclude_pgn).open(encoding='utf-8') as f:
            while record:=chess.pgn.read_game(f):
                board=record.board()
                for move in list(record.mainline_moves())[:8]: board.push(move)
                seen.add(board.fen())
    excluded=len(seen)
    for row in rows:
        board=chess.Board(); moves=[]
        for san in row['moves_san'].split()[:8]:
            move=board.parse_san(san); moves.append(move); board.push(move)
        if board.fen() in seen or board.is_game_over(claim_draw=True): continue
        seen.add(board.fen()); openings.append(moves)
        if len(openings)==a.pairs: break
    assert len(openings)==a.pairs
    games=[]
    for pair,moves in enumerate(openings):
        for candidate_white in (True,False):
            board=chess.Board(); hist=[]
            for move in moves:
                hist.append(canonicalize_move(move.uci(),fastchess.WHITE if board.turn else fastchess.BLACK)); board.push(move)
            games.append(dict(pair=pair,candidate_white=candidate_white,board=board,history=hist,done=False,plies=0))
    last_progress=0
    while any(not g['done'] for g in games):
        for index,model in enumerate(models):
            group=[g for g in games if not g['done'] and int(g['board'].turn==g['candidate_white'])==index]
            for start in range(0,len(group),32):
                chunk=group[start:start+32]; boards=[]; ids=[]; masks=[]; legal=[]
                for g in chunk:
                    b=fastchess.Board(g['board'].fen()); boards.append(board_to_tensor(b))
                    h,m,_=encode_history(g['history'],history,20); ids.append(h); masks.append(m); legal.append(legal_move_mask(b,policy))
                n=len(chunk)
                if not n: continue
                args=[torch.stack(boards),torch.stack(ids),torch.stack(masks),torch.full((n,),10),torch.full((n,),10),torch.full((n,),2),torch.tensor([[1.,0.]]*n)]
                with torch.no_grad():
                    logits=model(*(x.to(device) for x in args))[0]
                    selected=masked_policy_logits(logits,torch.stack(legal).to(device)).argmax(-1).tolist()
                for g,move_id in zip(chunk,selected):
                    canonical=id_to_move[move_id]; raw=canonical if g['board'].turn else mirror_move(canonical)
                    move=chess.Move.from_uci(raw); assert move in g['board'].legal_moves
                    g['history'].append(canonical); g['board'].push(move); g['plies']+=1
                    if g['board'].is_game_over(claim_draw=True) or g['plies']>=240:
                        g['done']=True; result=g['board'].result(claim_draw=True)
                        g['result']=result if result!='*' else '1/2-1/2'
                        g['ply_limit_draw']=result=='*'
        completed=sum(g['done'] for g in games)
        if completed//10>last_progress:
            print(f'completed {completed}/{len(games)}',flush=True); last_progress=completed//10
    scores=[]; results=[]
    for pair in range(a.pairs):
        score=0
        for g in [x for x in games if x['pair']==pair]:
            r=g['result']; points=.5 if r=='1/2-1/2' else float((r=='1-0')==g['candidate_white'])
            score+=points
            results.append({k:g[k] for k in ('pair','candidate_white','result','ply_limit_draw','plies')})
        scores.append(score/2)
    rng=random.Random(20261022)
    boot=sorted(sum(rng.choices(scores,k=len(scores)))/len(scores) for _ in range(10000))
    report={'games':len(games),'candidate_score':sum(scores)/len(scores),'paired_bootstrap_95':[boot[250],boot[9749]],
        'split':a.split,'excluded_opening_positions':excluded,
        'original_sha256':hashlib.sha256(Path(a.original).read_bytes()).hexdigest(),
        'candidate_sha256':hashlib.sha256(Path(a.candidate).read_bytes()).hexdigest(),
        'conditioning':'Both Elo bucket 10 (>=2000), TC bucket 2, clock=[1,0]; argmax legal policy',
        'limitations':['Not a real-time 3+0 tournament','Paired held-out human opening sample','240-ply limit draws','No general Elo strength estimate'],
        'results':results}
    Path(a.out).write_text(json.dumps(report,indent=2),encoding='utf-8')
    with Path(a.out).with_suffix('.pgn').open('w',encoding='utf-8') as f:
        for g in games:
            record=chess.pgn.Game.from_board(g['board']); record.headers['Result']=g['result']
            record.headers['White']='Candidate' if g['candidate_white'] else 'Original'
            record.headers['Black']='Original' if g['candidate_white'] else 'Candidate'
            record.headers['Round']=str(g['pair']+1)
            record.headers['Termination']='ply-limit adjudication' if g['ply_limit_draw'] else 'normal'
            f.write(str(record)+'\n\n')
    print(json.dumps(report),flush=True)

if __name__=='__main__': main()
