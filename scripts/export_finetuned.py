"""Export a strict-loaded candidate and check ONNX against PyTorch on held-out boards."""
import argparse, hashlib, json
from pathlib import Path
import numpy as np
import onnx, onnxruntime as ort, torch
from onnxruntime.transformers import float16
from onnxruntime.transformers.onnx_model import OnnxModel
from safetensors.torch import load_file
from data_loader import StreamConfig, create_data_loader
from train import build_model

NAMES=['board','history_ids','history_mask','active_elo','opponent_elo','tc','clock']
KEYS=['board','history_ids','history_mask','active_elo_bucket','opponent_elo_bucket','time_control_bucket','clock_features']

def main():
    p=argparse.ArgumentParser(); p.add_argument('--weights',required=True); p.add_argument('--data',required=True); p.add_argument('--out',required=True)
    a=p.parse_args(); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    torch.set_num_threads(8); torch.backends.mha.set_fastpath_enabled(False)
    model=build_model(20); model.load_state_dict(load_file(a.weights),strict=True); model.eval()
    loader=create_data_loader(StreamConfig(data_dir=a.data,months=['test'],batch_size=1,positions_per_game=8,shuffle_files=True))
    batches=[]
    for batch in loader:
        batches.append(batch)
        if len(batches)==64: break
    for fraction in (0., .01, .5, 1., 2.):
        batch={k:v.clone() if isinstance(v,torch.Tensor) else v for k,v in batches[0].items()}
        batch['history_ids'].zero_(); batch['history_mask'].zero_()
        batch['clock_features']=torch.tensor([[fraction,0.]])
        batches.append(batch)
    args=tuple(batches[0][k] for k in KEYS)
    fp32=out/'candidate_fp32.onnx'; fp16=out/'candidate_fp16.onnx'
    torch.onnx.export(model,args,str(fp32),opset_version=15,dynamo=False,
        input_names=NAMES,output_names=['policy_logits','aux_logits','value_pred'],
        dynamic_axes={name:{0:'batch_size'} for name in NAMES+['policy_logits','aux_logits','value_pred']})
    graph=onnx.load(str(fp32)); onnx.checker.check_model(graph)
    graph=float16.convert_float_to_float16(graph,keep_io_types=False,min_positive_val=1e-7,max_finite_val=1e4)
    OnnxModel(graph).topological_sort()
    graph.ir_version=min(graph.ir_version,10)
    onnx.save(graph,str(fp16)); onnx.checker.check_model(graph)
    options=ort.SessionOptions()
    options.intra_op_num_threads=4
    # Avoid a native FP16 fusion crash seen with ORT 1.31 on this Windows CPU.
    options.graph_optimization_level=ort.GraphOptimizationLevel.ORT_DISABLE_ALL
    session=ort.InferenceSession(str(fp16),sess_options=options,providers=['CPUExecutionProvider'])
    maximum=0.; same=0; max_probability_difference=0.; disagreements=[]
    with torch.no_grad():
        for index,batch in enumerate(batches):
            args=tuple(batch[k] for k in KEYS); reference=model(*args)[0].numpy()
            feeds={item.name:x.numpy().astype(np.float16) if item.type=='tensor(float16)' else x.numpy()
                   for item,x in zip(session.get_inputs(),args)}
            actual=session.run(None,feeds)[0].astype(np.float32)
            assert np.isfinite(actual).all()
            legal=batch['legal_move_mask'].numpy(); ref=np.where(legal,reference,-1e9); pred=np.where(legal,actual,-1e9)
            same+=int(ref.argmax()==pred.argmax()); maximum=max(maximum,float(np.abs(reference-actual).max()))
            valid=legal[0]; rp=reference[0,valid]; ap=actual[0,valid]
            rp=np.exp(rp-rp.max()); rp/=rp.sum(); ap=np.exp(ap-ap.max()); ap/=ap.sum()
            max_probability_difference=max(max_probability_difference,float(np.abs(rp-ap).max()))
            if ref.argmax()!=pred.argmax():
                disagreements.append({'sample':index,'reference_move_id':int(ref.argmax()),'onnx_move_id':int(pred.argmax()),
                    'reference_logit_gap':float(ref[0,ref.argmax()]-ref[0,pred.argmax()]),
                    'maximum_probability_difference':float(np.abs(rp-ap).max())})
    report={'boards':len(batches),'same_legal_top_move':same,'maximum_logit_difference':maximum,
        'maximum_probability_difference':max_probability_difference,'disagreements':disagreements,
        'probability_tolerance':.01,'near_tie_logit_tolerance':.01,
        'passed':max_probability_difference<=.01 and all(x['reference_logit_gap']<=.01 for x in disagreements),
        'onnx_sha256':hashlib.sha256(fp16.read_bytes()).hexdigest(),'bytes':fp16.stat().st_size}
    (out/'export-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    # FP16 can exchange almost tied top moves; bound the entire legal probability vector.
    assert report['passed'],report
    print(json.dumps(report),flush=True)

if __name__=='__main__': main()
