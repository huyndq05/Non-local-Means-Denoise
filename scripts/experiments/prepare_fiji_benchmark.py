from pathlib import Path
from zipfile import ZipFile
import json,hashlib
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/fiji_reference_20261116/gaussian_benchmark';OUT.mkdir(parents=True,exist_ok=True)
items=[]
for zpath in sorted((ROOT/'results/baseline_v2').glob('*_Gaussian_*_s42.zip')):
    image=zpath.name[:2]
    if image in ['06','09']:continue
    split='illustration' if image=='02' else 'test'
    case=OUT/zpath.stem;case.mkdir(exist_ok=True)
    with ZipFile(zpath) as z:
        meta=json.loads(z.read('metadata.json'))
        for src,dst in [('source_gray.png','source_gray.png'),('noisy_input.png','noisy_input.png'),(meta['files']['NLM tự cài đặt'],'python_nlm.png')]:
            (case/dst).write_bytes(z.read(src))
        assert meta['shape']==[256,256]
    items.append(dict(id=zpath.stem,image=image,split=split,sigma=meta['noise']['level'],path=case.relative_to(ROOT).as_posix(),source_zip=zpath.relative_to(ROOT).as_posix(),source_sha256=hashlib.sha256(zpath.read_bytes()).hexdigest(),python_parameters=meta['parameters']))
(OUT/'manifest.json').write_text(json.dumps({'cases':items,'seed':42,'plugin_command':'Non-local Means Denoising','plugin_factor':1,'auto_estimate_sigma':False,'shape':[256,256],'scope':'30 test cases, 3 separate illustrations; matched to stored Python input PNGs'},ensure_ascii=False,indent=2),encoding='utf-8')
print('Prepared',len(items),'paired inputs, including 30 evaluation cases.')
