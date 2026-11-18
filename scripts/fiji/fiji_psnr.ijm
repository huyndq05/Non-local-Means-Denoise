// ImageJ1 macro. Compare two aligned grayscale 8-bit images, full frame.
gtPath = File.openDialog("Select grayscale 8-bit ground truth");
open(gtPath); gtOriginal = getImageID();
if (bitDepth != 8) exit("Ground truth must be 8-bit grayscale.");
getDimensions(w, h, c, z, t);
if (c*z*t != 1) exit("Use a single 2D image.");
run("Duplicate...", "title=NLM_GT_METRIC_COPY"); gt = getImageID();
run("Select None"); run("32-bit");
resultPath = File.openDialog("Select aligned 8-bit result");
open(resultPath); resultOriginal = getImageID();
if (bitDepth != 8) exit("Result must be 8-bit grayscale.");
getDimensions(w2, h2, c2, z2, t2);
if (w != w2 || h != h2 || c2*z2*t2 != 1) exit("Image dimensions differ.");
run("Duplicate...", "title=NLM_RESULT_METRIC_COPY"); result = getImageID();
run("Select None"); run("32-bit");
imageCalculator("Subtract create 32-bit", gt, result);
errorImage = getImageID();
run("Square");
run("Select None"); resetThreshold();
getStatistics(area, mse, min, max, std);
if (mse == 0) print("MSE=0; PSNR=Infinity");
else print("MSE="+d2s(mse,8)+"; PSNR_dB="+d2s(10*log(255*255/mse)/log(10),8));
print("GT: "+gtPath); print("Result: "+resultPath);
// Keep original input windows. Close only generated metric copies.
selectImage(errorImage); close(); selectImage(gt); close(); selectImage(result); close();
