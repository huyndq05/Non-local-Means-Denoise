"""Run paired baseline experiments. python scripts/benchmark_nlm.py --help"""
import argparse
import hashlib
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import numpy as np
import pandas as pd
from nlm_lab import load_image, noise, metrics, png
from experiment import METHODS, DEFAULTS, benchmark, package, csv_bytes


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',default='data/clean_gray')
    parser.add_argument('--output',default='results/baseline_v2')
    parser.add_argument('--size',type=int,default=256,help='Center crop side, no resizing')
    parser.add_argument('--max-images',type=int,default=13)
    parser.add_argument('--repeats',type=int,default=3)
    parser.add_argument('--seeds',type=int,nargs='+',default=[42])
    parser.add_argument('--radius',type=int,default=5)
    args=parser.parse_args()
    if args.size<7 or not 0<=args.radius<=20 or not 1<=args.repeats<=20:
        parser.error('size >= 7, radius 0..20, repeats 1..20')
    out=Path(args.output); out.mkdir(parents=True,exist_ok=True)
    rows=[]; manifest=[]
    files=sorted(Path(args.input).glob('*.png'))[:args.max_images]
    if not files: parser.error('No input images')
    conditions=[('Gaussian',v) for v in [10,20,30]]+ [('Salt and pepper',v) for v in [.01,.05,.1]]+ [('Poisson',v) for v in [10,30,100]]
    for file in files:
        x=load_image(file)
        side=min(args.size,*x.shape); y=(x.shape[0]-side)//2; z=(x.shape[1]-side)//2
        x=x[y:y+side,z:z+side].copy()
        split='calibration' if file.name[:2] in ['02','06','09'] else 'test'
        for kind,level in conditions:
            for seed in args.seeds:
                noisy=noise(x,kind,level,seed)
                p=DEFAULTS.copy(); p['radius']=args.radius
                # Gaussian known sigma; non-Gaussian fixed 20 is explicitly a baseline.
                p['sigma']=float(level) if kind=='Gaussian' else 20.
                p['h']=.4*p['sigma']; p['peak']=float(level) if kind=='Poisson' else 30.
                selected=METHODS[:6]+(['Median + NLM'] if kind=='Salt and pepper' else ['Anscombe + NLM'] if kind=='Poisson' else [])
                results=benchmark(noisy,selected,p,args.repeats,True)
                cfg=dict(kind=kind,level=level,seed=seed)
                payload,items,_=package(x,noisy,results,p,cfg,True,file.name,repeats=args.repeats,warmup=True)
                stem=f'{file.stem}_{kind.replace(" ","")}_{level}_s{seed}'
                (out/(stem+'.zip')).write_bytes(payload)
                for row in items:
                    rows.append(dict(image=file.name,split=split,noise=kind,level=level,seed=seed,
                                     height=side,width=side,**row))
                manifest.append(dict(id=stem,source=str(file),crop_xywh=[z,y,side,side],split=split,
                                     noise=cfg,input_png_sha256=hashlib.sha256(png(noisy)).hexdigest()))
        print(f'Completed {file.name}',flush=True)
    (out/'metrics.csv').write_bytes(csv_bytes(rows))
    # First aggregate repeated seeds within image, then images within split.
    df=pd.DataFrame(rows)
    per_image=df.groupby(['image','split','noise','level','method'],as_index=False)[['MSE','PSNR_dB','SSIM','seconds']].mean()
    summary=per_image.groupby(['split','noise','level','method']).agg(n=('image','nunique'),
        PSNR_mean=('PSNR_dB','mean'),PSNR_sd=('PSNR_dB','std'),SSIM_mean=('SSIM','mean'),
        MSE_mean=('MSE','mean'),seconds_mean=('seconds','mean')).reset_index()
    summary.to_csv(out/'summary.csv',index=False,encoding='utf-8-sig')
    (out/'manifest.json').write_text(json.dumps(dict(protocol='fixed baseline, center crops, no parameter tuning, paired input',
        args=vars(args),items=manifest),ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'{len(manifest)} paired inputs; {len(rows)} metric rows; saved in {out}',flush=True)


if __name__=='__main__': main()
