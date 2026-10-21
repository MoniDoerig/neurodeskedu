using CLEARSWI

TEs = [20]
nifti_folder = joinpath(homedir(), "neurodesktop-storage/swi-demo/01_bids/sub-170705134431std1312211075243167001/ses-1/anat")
magfile = joinpath(nifti_folder, "sub-170705134431std1312211075243167001_ses-1_run-1_part-mag_T2starw.nii")
phasefile = joinpath(nifti_folder, "sub-170705134431std1312211075243167001_ses-1_run-1_part-phase_T2starw.nii")

println("Loading magnitude and phase data...")
mag = readmag(magfile);
phase = readphase(phasefile);
data = Data(mag, phase, mag.header, TEs);

println("Computing SWI...")
swi = calculateSWI(data);

println("Creating minimum intensity projection...")
mip = createMIP(swi);

outdir = joinpath(homedir(), "neurodesktop-storage/swi-demo")
println("Saving outputs...")
savenii(swi, joinpath(outdir, "swi.nii"); header=mag.header)
savenii(mip, joinpath(outdir, "mip.nii"); header=mag.header)

println("Done! Output saved to ~/neurodesktop-storage/swi-demo/")
