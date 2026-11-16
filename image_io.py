"""Lossless 8/16-bit grayscale/RGB I/O and explicit display conversion."""
import io
from pathlib import Path
import numpy as np
import png as png_codec
import tifffile
from PIL import Image, ImageOps


def intensity_range(image):
    return 65535. if np.asarray(image).dtype == np.uint16 else 255.


def quantize(image, dtype=np.uint8):
    dtype=np.dtype(dtype)
    if dtype not in (np.dtype('uint8'),np.dtype('uint16')):
        raise ValueError('Đầu ra chỉ hỗ trợ uint8 hoặc uint16.')
    return np.rint(np.clip(image,0,np.iinfo(dtype).max)).astype(dtype)


def preview(image):
    """Fixed full-range preview only; never used for filtering or metrics."""
    return quantize(np.asarray(image,dtype=float)*255/intensity_range(image))


def orient(array, orientation):
    if orientation==2:return np.flip(array,1)
    if orientation==3:return np.rot90(array,2)
    if orientation==4:return np.flip(array,0)
    if orientation==5:return np.swapaxes(array,0,1)
    if orientation==6:return np.rot90(array,-1)
    if orientation==7:return np.flip(np.swapaxes(array,0,1),(0,1))
    if orientation==8:return np.rot90(array,1)
    return array


def load_image(file, color=False):
    """color=False preserves the old grayscale benchmark API; UI opts into RGB."""
    if isinstance(file,(str,Path)):
        raw=Path(file).read_bytes()
    else:
        file.seek(0);raw=file.read()
    associated_alpha=False
    if raw[:4] in (b'II*\x00',b'MM\x00*',b'II+\x00',b'MM\x00+'):
        with tifffile.TiffFile(io.BytesIO(raw)) as tif:
            series=tif.series[0]
            if len(tif.series)!=1 or series.axes not in ('YX','YXS','SYX'):
                raise ValueError('Chỉ nhận TIFF 2D đơn hoặc RGB, không nhận stack/volume.')
            a=series.asarray()
            if series.axes=='SYX':a=np.moveaxis(a,0,-1)
            if a.ndim==3 and (tif.pages[0].photometric.name!='RGB' or a.shape[-1] not in (3,4)):
                raise ValueError('TIFF nhiều kênh phải là RGB/RGBA.')
            tag=tif.pages[0].tags.get('Orientation')
            a=orient(a,int(tag.value) if tag else 1)
            associated_alpha=bool(tif.pages[0].extrasamples and int(tif.pages[0].extrasamples[0])==1)
    elif raw.startswith(b'\x89PNG\r\n\x1a\n') and raw[24]==16:
        w,h,rows,info=png_codec.Reader(bytes=raw).asDirect()
        a=np.vstack([np.asarray(row,dtype=np.uint16) for row in rows]).reshape(h,w,info['planes'])
        if a.shape[-1]==1:a=a[...,0]
        with Image.open(io.BytesIO(raw)) as im:
            a=orient(a,int(im.getexif().get(274,1)))
    else:
        with Image.open(io.BytesIO(raw)) as im:
            if getattr(im,'n_frames',1)!=1:
                raise ValueError('Chỉ nhận một ảnh tĩnh, không nhận ảnh động/stack.')
            im=ImageOps.exif_transpose(im)
            if im.mode in ('F','I') or im.mode.startswith('I;16'):
                a=np.asarray(im).copy()
            else:
                a=np.asarray(im.convert('RGBA') if 'transparency' in im.info or im.mode=='RGBA' else im.convert('RGB') if im.mode not in ('1','L') else im.convert('L')).copy()
    if a.dtype.kind!='u' or a.dtype.itemsize not in (1,2):
        raise ValueError('Hỗ trợ ảnh 8-bit/16-bit không dấu. TIFF float 32-bit cần chuyển miền cường độ có chủ đích trước khi tải.')
    a=a.astype(np.uint16 if a.dtype.itemsize==2 else np.uint8)
    if a.ndim not in (2,3) or (a.ndim==3 and a.shape[-1] not in (2,3,4)):
        raise ValueError('Ảnh phải là ảnh xám, RGB hoặc RGBA 2D.')
    if a.ndim==3 and a.shape[-1] in (2,4):
        maximum=intensity_range(a); alpha=a[...,-1:].astype(float)/maximum
        channels=a[...,:-1].astype(float)
        a=quantize((channels if associated_alpha else channels*alpha)+maximum*(1-alpha),a.dtype)
        if a.shape[-1]==1:a=a[...,0]
    if a.ndim==3 and not color:
        a=np.asarray(Image.fromarray(a).convert('L')).copy() if a.dtype==np.uint8 else quantize(a.astype(float)@np.array([.299,.587,.114]),np.uint16)
    return np.ascontiguousarray(a)


def png(image):
    image=np.asarray(image)
    if image.dtype!=np.uint16:
        image=quantize(image)
    buf=io.BytesIO()
    if image.dtype==np.uint16:
        rgb=image.ndim==3
        writer=png_codec.Writer(width=image.shape[1],height=image.shape[0],greyscale=not rgb,bitdepth=16)
        writer.write(buf,image.reshape(image.shape[0],-1).tolist())
    else:
        Image.fromarray(image).save(buf,format='PNG')
    return buf.getvalue()
