"""Controlled one-factor NLM study on three fixed calibration crops."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import pandas as pd
from nlm_lab import load_image, noise, metrics
from experiment import DEFAULTS, benchmark, csv_bytes


def main():
    rows=[]
    for file in sorted((ROOT/'data/clean_gray').glob('*.png')):
        if file.name[:2] not in ['02','06','09']: continue
        x=load_image(file); y=(x.shape[0]-256)//2; z=(x.shape[1]-256)//2
        x=x[y:y+256,z:z+256]; v=noise(x,'Gaussian',20,42)
        for variable,values in [('factor',[.2,.4,.6,.8,1.]),('patch',[3,5,7,9]),('radius',[2,3,5,7,10])]:
            for value in values:
                p=DEFAULTS.copy()
                if variable=='factor': p['h']=20*value
                else: p[variable]=value
                rec=benchmark(v,['NLM tự cài đặt'],p,3,True)['NLM tự cài đặt']
                rows.append(dict(image=file.name,variable=variable,value=value,**p,
                                 **metrics(x,rec['image']),seconds=rec['seconds']))
    out=ROOT/'results/sweep_v2'; out.mkdir(exist_ok=True,parents=True)
    (out/'metrics.csv').write_bytes(csv_bytes(rows))
    pd.DataFrame(rows).groupby(['variable','value']).agg(n=('image','count'),PSNR=('PSNR_dB','mean'),
        SSIM=('SSIM','mean'),seconds=('seconds','mean')).reset_index().to_csv(out/'summary.csv',index=False,encoding='utf-8-sig')
    print('Saved 42 calibration configurations; each uses 3 timing repeats after warmup.')


if __name__=='__main__': main()
