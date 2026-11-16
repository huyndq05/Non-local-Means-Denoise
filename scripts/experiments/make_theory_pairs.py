"""Paired teaching illustrations from the same saved 256-pixel inputs."""
import sys, io, json, zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'report/figures/bo_sung_20261113'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':17,'savefig.facecolor':'white'})
manifest={}

def read(kind,level):
    source=next((ROOT/'results/baseline_v2').glob(f'02_*_{kind}_{level}_s42.zip'))
    with zipfile.ZipFile(source) as z:
        meta=json.loads(z.read('metadata.json'))
        def arr(name):return np.asarray(Image.open(io.BytesIO(z.read(name))))
        clean,noisy=arr('source_gray.png'),arr('noisy_input.png')
        outputs={name:arr(file) for name,file in meta['files'].items()}
    assert clean.shape==noisy.shape==(256,256)
    return clean,noisy,outputs,str(source.relative_to(ROOT))

def pair(number,a,b,left,right,source):
    fig,axes=plt.subplots(1,2,figsize=(8.2,4.3))
    for ax,x,label in zip(axes,[a,b],[left,right]):
        ax.imshow(x,cmap='gray',vmin=0,vmax=255,interpolation='nearest')
        ax.set_title(label,pad=8);ax.axis('off')
    fig.tight_layout(pad=.5,w_pad=1)
    name=f'theory_{number}.png';fig.savefig(OUT/name,dpi=220,bbox_inches='tight',pad_inches=.08);plt.close(fig)
    manifest[number]={'path':str((OUT/name).relative_to(ROOT)),'source':source,'shape_each':[256,256],'left':left,'right':right}

u,g,outputs,source=read('Gaussian',20)
pair('2_1',u,g,'Ảnh gốc','Nhiễu Gaussian',source)
u,sp,_,spsource=read('Saltandpepper',0.05)
pair('2_2',u,sp,'Ảnh gốc','Nhiễu muối tiêu',spsource)
u,po,_,posource=read('Poisson',30)
pair('2_3',u,po,'Ảnh gốc','Nhiễu Poisson',posource)
for num,method,label in [('2_4','Mean','Lọc trung bình'),('2_5','Gaussian','Lọc Gaussian'),('2_7','Bilateral','Lọc bilateral'),('2_8','NLM tự cài đặt','Lọc Non-Local Means')]:
    pair(num,g,outputs[method],'Ảnh nhiễu Gaussian',label,source)
_,_,spoutputs,_=read('Saltandpepper',0.05)
pair('2_6',sp,spoutputs['Median'],'Ảnh nhiễu muối tiêu','Lọc trung vị',spsource)
(OUT/'theory_pairs_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('Generated 8 paired illustrations, 256x256 per panel.')
