"""Scientific figures from the stored baseline ZIPs and calibration CSVs."""
import csv
import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np
import pandas as pd
from nlm_lab import load_image, filter_image, u8, metrics

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/report_figures';OUT.mkdir(parents=True,exist_ok=True)
BASE=ROOT/'results/baseline_v2'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':15,'axes.titlesize':16,
                     'axes.labelsize':14,'xtick.labelsize':12,'ytick.labelsize':12,
                     'savefig.facecolor':'white','axes.spines.top':False,'axes.spines.right':False})
TEAL='#087f8c';ORANGE='#d16b24';BLUE='#315da8'
manifest={}


def baseline(kind,level,prefix='10'):
    file=next(BASE.glob(f'{prefix}_*_{kind.replace(" ","")}_{level}_s42.zip'))
    with zipfile.ZipFile(file) as z:
        meta=json.loads(z.read('metadata.json'))
        images={name:load_image(io.BytesIO(z.read(filename))) for name,filename in meta['files'].items()}
        clean=load_image(io.BytesIO(z.read('source_gray.png')))
        noisy=load_image(io.BytesIO(z.read('noisy_input.png')))
    return clean,noisy,images,meta,str(file.relative_to(ROOT))


def image(ax,a,title):
    ax.imshow(a,cmap='gray',vmin=0,vmax=255,interpolation='nearest');ax.set_title(title,pad=7);ax.axis('off')


def finish(fig,number,caption,sources,width=6.35):
    name='fig_'+number.replace('.','_')+'.png';p=OUT/name
    fig.savefig(p,dpi=190,bbox_inches='tight',pad_inches=.12);plt.close(fig)
    manifest[number]=dict(path=str(p.relative_to(ROOT)),caption=caption,sources=sources,width_inches=width,
                          sha256=hashlib.sha256(p.read_bytes()).hexdigest())


# 2.1 is a workflow diagram, not a claim that Fiji runs have been completed.
fig,ax=plt.subplots(figsize=(12,3.5));ax.set_xlim(0,12);ax.set_ylim(0,3.5);ax.axis('off')
nodes=[(.8,1.7,'Ảnh sạch u'),(3,1.7,'Sinh nhiễu\nseed cố định'),(5.5,1.7,'PNG chung v'),
       (8,2.6,'Python\nđã có số đo'),(8,.7,'Fiji\nthu minh chứng'),(10.8,1.7,'Đánh giá\nMSE / PSNR / SSIM')]
for x,y,label in nodes:
    ax.text(x,y,label,ha='center',va='center',fontsize=17,bbox=dict(boxstyle='round,pad=.5',fc='#f0f5f8',ec='#8297a5'))
for start,end in [((1.7,1.7),(2.1,1.7)),((3.9,1.7),(4.6,1.7)),((6.4,1.9),(7.1,2.5)),((6.4,1.5),(7.1,.8)),((8.9,2.5),(9.8,1.9)),((8.9,.8),(9.8,1.5))]:
    ax.annotate('',xy=end,xytext=start,arrowprops=dict(arrowstyle='->',lw=1.6,color=TEAL))
finish(fig,'2.1','Hình 2.1. Quy trình đối chiếu dùng chung PNG nhiễu; Fiji là nhánh cần thu minh chứng thực hành.',['Sơ đồ phương pháp từ mã dự án'])

clean,noisy,outputs,meta,src=baseline('Gaussian',20)
# 2.2 shows exact stored PNGs and residual histograms after 8-bit clipping.
fig,axes=plt.subplots(2,4,figsize=(13.5,6.3),gridspec_kw={'height_ratios':[1, .8]})
image(axes[0,0],clean,'Ảnh sạch · 10')
axes[1,0].axis('off');axes[1,0].text(0,.9,'Crop giữa 256 × 256\nSeed 42\nHistogram sau clip 8-bit\nPhần dư = v − u',va='top',fontsize=16)
sources=[]
for col,sigma in enumerate([10,20,30],1):
    x,v,_,_,source=baseline('Gaussian',sigma);sources.append(source)
    image(axes[0,col],v,f'Gaussian σ = {sigma}')
    residual=v.astype(float)-x.astype(float)
    axes[1,col].hist(residual.ravel(),bins=np.arange(-100,105,5),density=True,color=TEAL,alpha=.85)
    axes[1,col].set_xlim(-100,100);axes[1,col].set_ylim(0,.047)
    axes[1,col].set_xlabel('Phần dư (mức xám)');axes[1,col].set_title(f'SD thực = {residual.std():.2f}',fontsize=14)
fig.tight_layout()
finish(fig,'2.2','Hình 2.2. Crop ảnh 10 với Gaussian σ = 10, 20, 30 và histogram phần dư sau clip, seed 42.',sources)

u,v,out,m,source=baseline('Salt and pepper',.05)
fig,axes=plt.subplots(1,4,figsize=(13,3.45))
for ax,a,title in zip(axes,[u,v,out['Median'],out['NLM tự cài đặt']],['Sạch','Muối tiêu p = 0,05','Median 3 × 3','NLM P5, r5, h8']):image(ax,a,title)
fig.tight_layout()
finish(fig,'2.3','Hình 2.3. Cùng crop ảnh 10: sạch, muối tiêu p = 0,05, Median và NLM tự cài; seed 42.',[source])

fig=plt.figure(figsize=(13.5,6));gs=fig.add_gridspec(2,3,height_ratios=[1,1.05])
sources=[];ax=fig.add_subplot(gs[1,:])
bins=np.arange(0,257,16)
for col,(peak,color) in enumerate(zip([10,30,100],[ORANGE,TEAL,BLUE])):
    u,v,_,_,source=baseline('Poisson',peak);sources.append(source)
    image(fig.add_subplot(gs[0,col]),v,f'Poisson peak = {peak}')
    residual=v.astype(float)-u.astype(float);centers=[];variances=[]
    for a,b in zip(bins[:-1],bins[1:]):
        mask=(u>=a)&(u<b)
        if mask.sum()>=30:centers.append(float(u[mask].mean()));variances.append(float(residual[mask].var()))
    ax.plot(centers,variances,'o-',color=color,label=f'Peak {peak}: đo sau clip')
    ax.plot([0,255],[0,255*255/peak],':',color=color,alpha=.7)
ax.set_xlabel('Cường độ sạch theo nhóm');ax.set_ylabel('Phương sai phần dư');ax.legend(fontsize=11,ncol=3)
ax.set_title('Nét chấm: phương sai lý thuyết 255u / peak trước clip',fontsize=13)
ax.grid(alpha=.2);fig.tight_layout()
finish(fig,'2.4','Hình 2.4. Poisson tại ba peak và phương sai phần dư theo nhóm cường độ; đường lý thuyết trước clip được vẽ nét chấm.',sources)

fig,axes=plt.subplots(2,6,figsize=(15,5.3))
sources=[]
for row,(kind,level,rowname) in enumerate([('Gaussian',20,'Gaussian 20'),('Salt and pepper',.05,'Muối tiêu 0,05')]):
    u,v,out,_,source=baseline(kind,level);sources.append(source)
    names=['Sạch','Nhiễu','Mean','Gaussian','Median','NLM tự cài']
    arrays=[u,v,out['Mean'],out['Gaussian'],out['Median'],out['NLM tự cài đặt']]
    for ax,a,title in zip(axes[row],arrays,names):image(ax,a,title)
    axes[row,0].text(-.12,.5,rowname,transform=axes[row,0].transAxes,rotation=90,ha='center',va='center',fontsize=13)
fig.tight_layout()
finish(fig,'3.1','Hình 3.1. So sánh cùng crop ảnh 10: Mean 3×3, Gaussian s=1, Median 3×3 và NLM P5/r5/h8; hai loại nhiễu, seed 42.',sources)

u,v,out,m,source=baseline('Gaussian',20)
fig,axes=plt.subplots(1,4,figsize=(13,3.45));arrays=[u,v];titles=['Sạch','Gaussian σ = 20']
for color in [10,40]:
    p=m['parameters'].copy();p['color']=color
    arrays.append(u8(filter_image(v,'Bilateral',p)));titles.append(f'Bilateral σr = {color}')
for ax,a,title in zip(axes,arrays,titles):image(ax,a,title)
fig.tight_layout()
finish(fig,'3.2','Hình 3.2. Bilateral trên ảnh 10, σ không gian=3 pixel, σ cường độ=10 và 40; cùng Gaussian20, seed42. Hai cấu hình được chạy bổ sung.',[source,'nlm_lab.filter_image; sigma_color 10/40, sigma_spatial 3'])

# 4.1: actual patch distances and weights at one chosen pixel.
u,v,_,m,source=baseline('Gaussian',20,prefix='02');cy=cx=128;f=2;r=10
target=v[cy-f:cy+f+1,cx-f:cx+f+1].astype(float);weights=np.zeros((21,21));candidates=[]
for dy in range(-r,r+1):
 for dx in range(-r,r+1):
    patch=v[cy+dy-f:cy+dy+f+1,cx+dx-f:cx+dx+f+1].astype(float)
    distance=float(np.mean((target-patch)**2));q=np.exp(-max(distance-800,0)/64)
    weights[dy+r,dx+r]=q
    if abs(dx)+abs(dy)>=5:candidates.append((q,dy,dx,patch))
selected=sorted(candidates,key=lambda z:-z[0])[::max(1,len(candidates)//3)][:3]
fig=plt.figure(figsize=(13,5.8));gs=fig.add_gridspec(2,5)
ax=fig.add_subplot(gs[:,0:2]);image(ax,v,'Ảnh nhiễu · tâm đỏ (128,128)')
ax.add_patch(Rectangle((cx-f-.5,cy-f-.5),5,5,fill=False,edgecolor='red',lw=2))
for q,dy,dx,pa in selected:ax.add_patch(Rectangle((cx+dx-f-.5,cy+dy-f-.5),5,5,fill=False,edgecolor='#00d4cf',lw=1.5))
image(fig.add_subplot(gs[0,2]),target,'Patch tâm')
for k,(q,dy,dx,pa) in enumerate(selected):image(fig.add_subplot(gs[1,k+2]),pa,f'Δ=({dx},{dy})\nq={q:.2g}')
ax=fig.add_subplot(gs[0,3:]);im=ax.imshow(weights,cmap='viridis',vmin=0,vmax=1,extent=[-10.5,10.5,10.5,-10.5]);ax.set_title('Trọng số q trong search 21 × 21');ax.set_xlabel('dx');ax.set_ylabel('dy');fig.colorbar(im,ax=ax,fraction=.045)
fig.tight_layout()
finish(fig,'4.1','Hình 4.1. Patch 5×5 và bản đồ trọng số tại tâm (x=128,y=128), ảnh02 Gaussian20. Dùng σ20, h8, search21×21 và self weight1.',[source,'Khoảng cách patch đều; q=exp(-max(d-800,0)/64)'])

# 4.2: new quality-only sweep, fixed h rather than h/sigma.
rows=[];sigmas=[5,10,15,20,25,30,40]
for prefix in ['02','06','09']:
    u,v,_,m,source=baseline('Gaussian',20,prefix)
    for sigma in sigmas:
        p=m['parameters'].copy();p['sigma']=sigma;p['h']=8
        result=u8(filter_image(v,'NLM tự cài đặt',p))
        rows.append(dict(image=prefix,sigma=sigma,h=8,patch=5,radius=5,**metrics(u,result)))
df=pd.DataFrame(rows);df.to_csv(OUT/'sigma_fixed_h.csv',index=False,encoding='utf-8-sig')
g=df.groupby('sigma')['PSNR_dB'];avg=g.mean();sd=g.std()
fig,ax=plt.subplots(figsize=(11,3.5));ax.errorbar(avg.index,avg,yerr=sd,fmt='o-',capsize=4,color=TEAL)
ax.axvline(20,color=ORANGE,ls='--',label='Sigma sinh nhiễu = 20');ax.set_xlabel('Sigma giả định của NLM');ax.set_ylabel('PSNR (dB)')
ax.set_title('Giữ h=8, P=5, r=5 · 3 ảnh hiệu chỉnh · trung bình ± SD');ax.legend();ax.grid(alpha=.2);fig.tight_layout()
finish(fig,'4.2','Hình 4.2. Khảo sát bổ sung σ giả định, giữ h8/P5/r5 trên ba crop hiệu chỉnh Gaussian20, seed42; thanh sai số là SD qua ba ảnh.', ['results/baseline_v2: ảnh02,06,09 Gaussian20',str((OUT/'sigma_fixed_h.csv').relative_to(ROOT))])

sweep=pd.read_csv(ROOT/'results/sweep_v2/metrics.csv')
fig,axes=plt.subplots(1,2,figsize=(12,3.8))
for ax,var,xlabel in zip(axes,['patch','radius'],['Cạnh patch P','Bán kính tìm kiếm r']):
    group=sweep[sweep.variable==var].groupby('value')[['PSNR_dB','seconds']].mean()
    a=ax.plot(group.index,group.PSNR_dB,'o-',color=TEAL,label='PSNR');ax.set_ylabel('PSNR (dB)',color=TEAL);ax.set_xlabel(xlabel);ax.set_xticks(group.index)
    right=ax.twinx();b=right.plot(group.index,group.seconds*1000,'s--',color=ORANGE,label='Thời gian');right.set_ylabel('Trung bình trung vị (ms)',color=ORANGE)
    ax.grid(alpha=.2);ax.legend(a+b,[l.get_label() for l in a+b],fontsize=11,loc='upper left')
fig.tight_layout()
finish(fig,'4.3','Hình 4.3. Chất lượng và chi phí theo P hoặc r, lấy từ CSV khảo sát ba crop hiệu chỉnh. Mỗi thời gian là trung vị ba lượt sau làm nóng; đường biểu diễn trung bình qua ảnh.', ['results/sweep_v2/metrics.csv'])

fig,axes=plt.subplots(1,3,figsize=(13,3.8))
for ax,var,xlabel in zip(axes,['factor','patch','radius'],['h / σ','Cạnh patch P','Bán kính r']):
    g=sweep[sweep.variable==var].groupby('value')['PSNR_dB'];avg=g.mean();sd=g.std()
    ax.plot(avg.index,avg,'o-',color=TEAL);ax.fill_between(avg.index,avg-sd,avg+sd,color=TEAL,alpha=.15)
    ax.set_xlabel(xlabel);ax.set_ylabel('PSNR (dB)');ax.set_xticks(avg.index);ax.grid(alpha=.2)
fig.tight_layout()
finish(fig,'6.2','Hình 6.2. PSNR theo h/σ, P và r trên ảnh02/06/09, Gaussian20 seed42; thay từng biến, vùng tô biểu diễn ±1 SD qua ba ảnh.', ['results/sweep_v2/metrics.csv'])

u,v,out,m,source=baseline('Gaussian',20)
fig,axes=plt.subplots(1,6,figsize=(15,3.1))
arrays=[u,v,out['Mean'],out['Gaussian'],out['NLM tự cài đặt'],out['NLM scikit-image']]
for ax,a,title in zip(axes,arrays,['Sạch','Nhiễu','Mean','Gaussian','NLM tự cài','NLM thư viện']):
    image(ax,a,title+'\n'+('Tham chiếu' if title=='Sạch' else f"{metrics(u,a)['PSNR_dB']:.2f} dB"))
fig.tight_layout()
finish(fig,'6.3','Hình 6.3. Cùng crop ảnh10 Gaussian20 và PSNR riêng ảnh; cấu hình đúng baseline. Các số này không phải trung bình10 ảnh.',[source])

fig=plt.figure(figsize=(15,6.4));gs=fig.add_gridspec(3,6,height_ratios=[1,1,.07],hspace=.35,wspace=.1)
axes=np.array([[fig.add_subplot(gs[row,col]) for col in range(6)] for row in range(2)]);sources=[]
for row,(kind,level,variant) in enumerate([('Salt and pepper',.05,'Median'),('Poisson',30,'Anscombe + NLM')]):
    u,v,out,m,source=baseline(kind,level);sources.append(source);a=out[variant]
    for ax,img,title in zip(axes[row,:4],[u,v,out['NLM tự cài đặt'],a],['Sạch','Nhiễu','NLM tự cài',variant]):image(ax,img,title)
    axes[row,0].text(-.13,.5,'p = 0,05' if row==0 else 'Peak = 30',transform=axes[row,0].transAxes,rotation=90,ha='center',va='center',fontsize=13)
    im=axes[row,4].imshow(v.astype(float)-a.astype(float),cmap='RdBu_r',vmin=-50,vmax=50);axes[row,4].set_title('Phần dư v − û');axes[row,4].axis('off')
    im2=axes[row,5].imshow(np.abs(u.astype(float)-a.astype(float)),cmap='magma',vmin=0,vmax=50);axes[row,5].set_title('Sai số |u − û|');axes[row,5].axis('off')
cb=fig.colorbar(im,cax=fig.add_subplot(gs[2,4]),orientation='horizontal');cb.set_label('Phần dư: ±50 mức',fontsize=11)
cb.ax.tick_params(labelsize=10)
cb=fig.colorbar(im2,cax=fig.add_subplot(gs[2,5]),orientation='horizontal');cb.set_label('Sai số: 0–50 mức',fontsize=11)
cb.ax.tick_params(labelsize=10)
finish(fig,'6.4','Hình 6.4. Muối tiêu0,05 và Poisson30 trên ảnh10. Phần dư và sai số tính từ Median (hàng trên) hoặc Anscombe+NLM (hàng dưới); dùng chung thang hiển thị, không dùng ảnh đã đổi thang để tính metric.',sources)

(OUT/'figures_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('Generated',len(manifest),'traceable figures in',OUT,flush=True)
