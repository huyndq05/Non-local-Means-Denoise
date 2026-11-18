import ij.*
import ij.io.*
import ij.process.*
import ij.measure.*
import ij.plugin.*
import groovy.json.*
import java.awt.*

def dir=new DirectoryChooser('Chọn thư mục gaussian_benchmark chứa manifest.json').getDirectory()
if(!dir) return
def manifest=new JsonSlurper().parse(new File(dir+'manifest.json'))
def rows=[]
def errors=[]
def measure={gt,im ->
    def a=gt.getProcessor().convertToFloatProcessor();def b=im.getProcessor().convertToFloatProcessor()
    def err=new FloatProcessor(gt.width,gt.height)
    for(int i=0;i<gt.width*gt.height;i++){double delta=a.getf(i)-b.getf(i);err.setf(i,(float)(delta*delta))}
    double mse=err.getStatistics().mean
    [mse,10*Math.log10(255*255/mse)]
}
manifest.cases.each { cfg ->
    def casePath=new File(dir,cfg.id).getPath()
    def gt=IJ.openImage(casePath+'/source_gray.png')
    def input=IJ.openImage(casePath+'/noisy_input.png')
    def py=IJ.openImage(casePath+'/python_nlm.png')
    def result=input.duplicate();result.setTitle('REPORT NLM Fiji '+cfg.id);result.show()
    IJ.run(result,'Non-local Means Denoising','sigma='+cfg.sigma+' smoothing_factor=1')
    new FileSaver(result).saveAsPng(casePath+'/fiji_nlm.png')
    def a=measure(gt,py);def b=measure(gt,result)
    rows.add([id:cfg.id,image:cfg.image,split:cfg.split,sigma:cfg.sigma,MSE_Python_output:a[0],PSNR_Python_output:a[1],MSE_Fiji_output:b[0],PSNR_Fiji_output:b[1]])
    IJ.log('REPORT '+cfg.id+' | Python='+a[1]+' dB | Fiji='+b[1]+' dB')
    result.changes=false;result.close();gt.close();input.close();py.close()
}
new File(dir+'metrics_measured_by_fiji.json').text=JsonOutput.prettyPrint(JsonOutput.toJson(rows))
new File(dir+'execution_info.json').text=JsonOutput.toJson([imagej:IJ.getVersion(),cases:rows.size(),filters:'NLM Fiji sigma=known Gaussian sigma, smoothing factor=1, auto off',measurement:'Independent full-image squared difference on FloatProcessor; PSNR peak255'])

def snap={win,file ->
    win.setAlwaysOnTop(true);win.toFront();IJ.wait(700)
    def b=win.getBounds()
    def shot=new ScreenGrabber().captureScreen()
    shot.setRoi(new Rectangle((int)b.x+7,(int)b.y,(int)b.width-14,(int)b.height-8))
    def crop=new ImagePlus('Actual window screenshot',shot.getProcessor().crop())
    new FileSaver(crop).saveAsPng(dir+file);shot.close();crop.close()
    win.setAlwaysOnTop(false)
}
// Real ImageJ montages. Each panel uses the unmodified stored pixel array.
[10,20,30].each { sigma ->
    def cfg=manifest.cases.find{it.image=='02' && it.sigma==sigma}
    def values=rows.find{it.id==cfg.id}
    def stack=new ImageStack(256,256)
    def specs=[['source_gray.png','Clean'],['noisy_input.png','Noisy sigma '+sigma],['python_nlm.png',String.format(java.util.Locale.US,'NLM Python %.2f dB',values.PSNR_Python_output)],['fiji_nlm.png',String.format(java.util.Locale.US,'NLM Fiji %.2f dB',values.PSNR_Fiji_output)]]
    specs.each{s ->def im=IJ.openImage(new File(dir,cfg.id).getPath()+'/'+s[0]);stack.addSlice(s[1],im.getProcessor().duplicate());im.close()}
    def montage=new MontageMaker().makeMontage2(new ImagePlus('REPORT paired stack',stack),2,2,1.0,1,4,1,12,true)
    montage.setTitle('REPORT Fiji - red door - Gaussian '+sigma+' - Python vs Fiji');montage.show()
    montage.getWindow().setLocation(70,80)
    new FileSaver(montage).saveAsPng(dir+'montage_sigma'+sigma+'.png')
    snap(montage.getWindow(),'screenshot_sigma'+sigma+'.png')
    montage.changes=false;montage.close()
}
def rt=new ResultsTable()
[10,20,30].each { sigma ->
    def rr=rows.findAll{it.split=='test' && it.sigma==sigma}
    double a=rr.collect{it.PSNR_Python_output}.sum()/rr.size()
    double b=rr.collect{it.PSNR_Fiji_output}.sum()/rr.size()
    rt.incrementCounter();rt.addValue('Sigma',sigma);rt.addValue('n images',rr.size())
    rt.addValue('PSNR Python dB',a);rt.addValue('PSNR Fiji dB',b);rt.addValue('Delta dB',b-a)
}
rt.setPrecision(6);rt.show('REPORT NLM Gaussian - 10 test images')
def win=WindowManager.getWindow('REPORT NLM Gaussian - 10 test images')
win.setBounds(100,120,950,250)
snap(win,'screenshot_summary.png')
rt.save(dir+'summary_fiji.csv')
println('Completed 30 test cases + 3 separate illustrations. Screenshots are real Fiji windows.')
