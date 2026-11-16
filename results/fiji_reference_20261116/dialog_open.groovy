import ij.*
new Thread({Thread.sleep(1200);def im=IJ.openImage("E:/Git/Non-local-Means-Denoise/results/fiji_reference_20261116/noisy_input.png");im.setTitle('NLM configuration - red door');im.show();IJ.run(im,'Non-local Means Denoising',null)} as Runnable).start()
println('Dialog scheduled')