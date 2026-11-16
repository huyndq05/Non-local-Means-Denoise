from pathlib import Path
import json,hashlib
import numpy as np
import pandas as pd
from PIL import Image
from skimage.metrics import structural_similarity
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/fiji_reference_20261116/gaussian_benchmark'
manifest=json.loads((OUT/'manifest.json').read_text(encoding='utf-8'))
measured=json.loads((OUT/'metrics_measured_by_fiji.json').read_text(encoding='utf-8'))
baseline=pd.read_csv(ROOT/'results/baseline_v2/metrics.csv')
rows=[]
for cfg in manifest['cases']:
    r=next(r.copy() for r in measured if r['id']==cfg['id'])
    folder=OUT/cfg['id'];gt=np.asarray(Image.open(folder/'source_gray.png'),dtype=float)
    assert gt.shape==(256,256)
    assert hashlib.sha256((ROOT/cfg['source_zip']).read_bytes()).hexdigest()==cfg['source_sha256']
    for name,file in [('Python_output','python_nlm.png'),('Fiji_output','fiji_nlm.png')]:
        arr=np.asarray(Image.open(folder/file),dtype=float);assert arr.shape==gt.shape
        mse=float(np.mean((gt-arr)**2));psnr=float(10*np.log10(255**2/mse))
        assert abs(mse-r['MSE_'+name])<1e-8 and abs(psnr-r['PSNR_'+name])<1e-8
        r['Python_check_MSE_'+name]=mse;r['Python_check_PSNR_'+name]=psnr
        r['SSIM_'+name]=float(structural_similarity(gt,arr,data_range=255,win_size=7,gaussian_weights=False,use_sample_covariance=True))
    base=baseline[(baseline.image.str.startswith(cfg['image']+'_'))&(baseline.noise=='Gaussian')&(baseline.level==cfg['sigma'])&(baseline.method=='NLM tự cài đặt')].iloc[0]
    assert abs(float(base.PSNR_dB)-r['PSNR_Python_output'])<1e-8
    r['delta_PSNR']=r['PSNR_Fiji_output']-r['PSNR_Python_output']
    rows.append(r)
df=pd.DataFrame(rows);df.to_csv(OUT/'metrics_verified.csv',index=False,encoding='utf-8-sig')
summary=[]
for sigma,g in df[df.split=='test'].groupby('sigma'):
    assert len(g)==10
    summary.append(dict(sigma=int(sigma),n=10,python_psnr=g.PSNR_Python_output.mean(),python_sd=g.PSNR_Python_output.std(),fiji_psnr=g.PSNR_Fiji_output.mean(),fiji_sd=g.PSNR_Fiji_output.std(),python_ssim=g.SSIM_Python_output.mean(),fiji_ssim=g.SSIM_Fiji_output.mean(),delta=g.delta_PSNR.mean(),fiji_wins=int((g.delta_PSNR>0).sum())))
pd.DataFrame(summary).to_csv(OUT/'summary_verified.csv',index=False,encoding='utf-8-sig')
(OUT/'verification.json').write_text(json.dumps({'cases':len(rows),'test_cases':30,'illustration_cases':3,'independent_MSE_PSNR_match_tolerance':1e-8,'SSIM_computed_by':'Python scikit-image on saved output PNGs for both methods','summary':summary},indent=2),encoding='utf-8')
print(pd.DataFrame(summary).to_string(index=False))
