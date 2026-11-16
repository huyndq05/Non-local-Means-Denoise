import ij.*
import ij.io.*
import ij.plugin.*
import ij.gui.*
def gd=GenericDialog.getInstance();if(gd==null)throw new Exception('No actual plugin dialog')
println('Dialog='+gd.title+' numeric='+gd.numericFields.collect{it.text})
gd.numericFields[0].text='20';gd.numericFields[1].text='1';gd.checkboxes.each{it.state=false}
gd.setLocation(150,120);gd.setAlwaysOnTop(true);gd.toFront();IJ.wait(500)
def shot=new ScreenGrabber().captureScreen();def b=gd.bounds;shot.setRoi(b);def crop=new ImagePlus('Actual plugin dialog',shot.getProcessor().crop());new FileSaver(crop).saveAsPng("E:/Git/Non-local-Means-Denoise/results/fiji_reference_20261116/screenshot_nlm_dialog.png");shot.close()
gd.actionPerformed(new java.awt.event.ActionEvent(gd.buttons[1],java.awt.event.ActionEvent.ACTION_PERFORMED,'Cancel'))
