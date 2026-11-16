import ij.*
import ij.io.*
import ij.process.*
import ij.measure.*
import ij.plugin.*
import java.awt.*
def dir="E:/Git/Non-local-Means-Denoise/results/fiji_reference_20261116/"
def gt=IJ.openImage(dir+'source_gray.png')
def input=IJ.openImage(dir+'noisy_input.png')
input.setTitle('02 Red door - Gaussian sigma 20');input.show()
def methods=[['NLM Fiji','Non-local Means Denoising','sigma=20 smoothing_factor=1','fiji_nlm.png'],['Mean Fiji','Mean...','radius=1','fiji_mean.png'],['Gaussian Fiji','Gaussian Blur...','sigma=1','fiji_gaussian.png'],['Median Fiji','Median...','radius=1','fiji_median.png']]
def outputs=[]
methods.each { m -> def im=input.duplicate();im.setTitle(m[0]);im.show();IJ.run(im,m[1],m[2]);new FileSaver(im).saveAsPng(dir+m[3]);outputs.add(im) }
def py=IJ.openImage(dir+'python_nlm.png');py.setTitle('NLM Python')
def rows=['output,file,MSE_Fiji,PSNR_Fiji']
([py]+outputs).eachWithIndex { im,k ->
 def a=gt.getProcessor().convertToFloatProcessor();def b=im.getProcessor().convertToFloatProcessor();def err=new FloatProcessor(gt.width,gt.height)
 for(int i=0;i<gt.width*gt.height;i++){double d=a.getf(i)-b.getf(i);err.setf(i,(float)(d*d))}
 double mse=err.getStatistics().mean;double psnr=10*Math.log10(255*255/mse)
 String fn=k==0?'python_nlm.png':methods[k-1][3]
 rows.add(im.title+','+fn+','+mse+','+psnr)
 IJ.log(String.format(java.util.Locale.US,'%s: MSE=%.10f; PSNR=%.10f dB',im.title,mse,psnr))
 if(k==1){def ei=new ImagePlus('Squared error - NLM Fiji',err);ei.show();IJ.run(ei,'Enhance Contrast','saturated=0.35');ei.getWindow().setLocation(50,160);ei.getCanvas().setMagnification(3);ei.getWindow().pack()}
}
new File(dir+'metrics_fiji.csv').text=rows.join('\n')+'\n'
IJ.log('Reference: 02 old building with red door; 256x256; Gaussian sigma=20; seed=42')
IJ.log('NLM sigma=20, smoothing factor=1, auto off; Mean/Median radius=1; Gaussian sigma=1 px')
new File(dir+'fiji_log.txt').text=IJ.getLog()
def stack=new ImageStack(gt.width,gt.height)
([gt,input]+outputs).eachWithIndex{ im,i -> stack.addSlice(['Clean','Noisy sigma20','NLM Fiji','Mean r1','Gaussian s1','Median r1'][i],im.getProcessor().duplicate()) }
def montage=new MontageMaker().makeMontage2(new ImagePlus('Comparison',stack),3,2,1.0,1,6,1,12,true)
montage.setTitle('Fiji reference - building with red door');montage.show();montage.getWindow().setLocation(40,90);montage.getWindow().setAlwaysOnTop(true);montage.getWindow().toFront()
IJ.wait(600)
def shot=new ScreenGrabber().captureImage();new FileSaver(shot).saveAsPng(dir+'screenshot_comparison.png');shot.close()
def ei=WindowManager.getImage('Squared error - NLM Fiji');WindowManager.setCurrentWindow(ei.window);ei.window.setAlwaysOnTop(true);ei.window.toFront();IJ.wait(800)
shot=new ScreenGrabber().captureImage();new FileSaver(shot).saveAsPng(dir+'screenshot_error.png');shot.close()
def log=WindowManager.getWindow('Log');log.setBounds(480,180,850,300);log.setAlwaysOnTop(true);log.toFront();IJ.wait(800)
shot=new ScreenGrabber().captureScreen();def bnd=log.bounds;shot.setRoi(bnd);def crop=new ImagePlus('Log screenshot',shot.getProcessor().crop());new FileSaver(crop).saveAsPng(dir+'screenshot_log.png');shot.close()
println('EXPERIMENT_DONE ImageJ '+IJ.getVersion())
