"""Continue the official policy training; never silently initialize random weights."""
import argparse, hashlib, json, sys
from pathlib import Path
import torch
from safetensors.torch import load_file, save_file
import train
from data_loader import StreamConfig, create_data_loader

def evaluate(model, data, split, cfg, device):
    loader=create_data_loader(StreamConfig(data_dir=data,months=[split],batch_size=32,num_workers=0,positions_per_game=8))
    totals={f'{g}:{b}':{'positions':0,'correct':0,'nll':0.0} for g in ('blitz','replay') for b in range(11)}
    model.eval()
    with torch.no_grad():
        for batch in loader:
            groups=['blitz' if tc=='180+0' else 'replay' for tc in batch['time_control']]
            batch=train.move_batch_to_device(batch,device)
            args=[batch[k] for k in ('board','history_ids','history_mask','active_elo_bucket','opponent_elo_bucket','time_control_bucket','clock_features')]
            logits=train.masked_policy_logits(model(*args)[0],batch['legal_move_mask'])
            losses=torch.nn.functional.cross_entropy(logits,batch['target_move_id'],reduction='none').tolist()
            correct=logits.argmax(-1).eq(batch['target_move_id']).tolist()
            for g,b,nll,ok in zip(groups,batch['active_elo_bucket'].tolist(),losses,correct):
                t=totals[f'{g}:{b}']; t['positions']+=1; t['correct']+=int(ok); t['nll']+=nll
    for key,t in totals.items():
        if not t['positions']: raise RuntimeError(f'{split}: missing {key}')
        t['accuracy']=t['correct']/t['positions']; t['nll']/=t['positions']
    return totals

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--data',required=True); p.add_argument('--weights',required=True)
    p.add_argument('--out',required=True); p.add_argument('--steps',type=int,default=3000)
    p.add_argument('--batch-size',type=int,default=32); p.add_argument('--device',default='cuda')
    p.add_argument('--baseline-only',action='store_true')
    p.add_argument('--baseline-report',default=None)
    a=p.parse_args(); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    if not a.baseline_only and (out/'policy_model').exists():
        raise RuntimeError('Choose a new run directory; existing checkpoints must not be mixed')
    if a.device=='cuda' and not torch.cuda.is_available(): raise RuntimeError('CUDA unavailable: choose CPU explicitly or install a CUDA build')
    torch.set_num_threads(8); device=torch.device(a.device)
    cfg=train.TrainConfig(train_months=['train'],val_months=['validation'],data_dir=a.data,
        init_safetensors=a.weights,train_steps=a.steps,batch_size=a.batch_size,num_workers=0,
        learning_rate=1e-5,min_lr=1e-7,val_interval=500,val_steps=100,
        save_dir=str(out),save_checkpoints=True,device=a.device,positions_per_game=8)
    baseline=train.build_model(20).to(device)
    baseline.load_state_dict(load_file(a.weights),strict=True)
    # Verify package and training models have the exact same tensors and outputs.
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'package'))
    from otter_chess.model import StrongPolicyModel
    runtime=StrongPolicyModel().to(device); runtime.load_state_dict(baseline.state_dict(),strict=True)
    batch=next(iter(create_data_loader(StreamConfig(data_dir=a.data,months=['validation'],batch_size=2))))
    batch=train.move_batch_to_device(batch,device); baseline.eval(); runtime.eval()
    args=[batch[k] for k in ('board','history_ids','history_mask','active_elo_bucket','opponent_elo_bucket','time_control_bucket','clock_features')]
    with torch.no_grad():
        for x,y in zip(baseline(*args),runtime(*args)): torch.testing.assert_close(x,y)
    del runtime
    report={'original_sha256':hashlib.sha256(Path(a.weights).read_bytes()).hexdigest(),
            'architecture_parity':True,'config':vars(cfg),'baseline':{},'candidate':{}}
    if a.baseline_report:
        previous=json.loads(Path(a.baseline_report).read_text(encoding='utf-8'))
        assert previous['original_sha256']==report['original_sha256']
        assert previous['config']['data_dir']==a.data
        assert set(previous['baseline'])=={'validation','test'}
        report['baseline']=previous['baseline']
        report['baseline_device']=previous['config']['device']
    else:
        for split in ('validation','test'):
            report['baseline'][split]=evaluate(baseline,a.data,split,cfg,device)
            print(json.dumps({'baseline':split,**report['baseline'][split]}),flush=True)
    (out/'comparison.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    if a.baseline_only: return
    del baseline
    train.train(cfg)
    # Only load checkpoints produced by this local training run; optimizer includes numpy scalars.
    checkpoint=torch.load(train.best_checkpoint_path(cfg),map_location='cpu',weights_only=False)
    report['candidate_step']=checkpoint['step']
    report['training']=json.loads(Path(train.metrics_path(cfg)).read_text(encoding='utf-8').strip().splitlines()[-1])
    candidate=train.build_model(20); candidate.load_state_dict(checkpoint['model_state_dict'],strict=True)
    save_file({k:v.contiguous() for k,v in candidate.state_dict().items()},str(out/'candidate.safetensors'))
    candidate.to(device)
    for split in ('validation','test'):
        report['candidate'][split]=evaluate(candidate,a.data,split,cfg,device)
    report['candidate_sha256']=hashlib.sha256((out/'candidate.safetensors').read_bytes()).hexdigest()
    report['strength_verified']=False
    report['note']='Human-move prediction is not a playing-strength tournament; public model is unchanged.'
    (out/'comparison.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report),flush=True)

if __name__=='__main__': main()
