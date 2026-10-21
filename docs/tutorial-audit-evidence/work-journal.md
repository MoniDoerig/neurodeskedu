# Neurodesk GUI tutorial audit

Audit date: 20 October 2026, Australia Brisbane.
Platform: Neurodesk Play America, `ghcr.io/neurodesk/neurodesktop:2026-10-07`, Ubuntu 24.04.5 LTS.

The priority is to follow the interactive GUI tutorials, verify their results, diagnose failures and replace screenshots. A tool responding to `--help`, a successful notebook execution and a completed GUI workflow are recorded separately. Screenshot moves preserve the original image and do not count as a refresh.

## Verified results

| Tutorial | Evidence so far | Remaining GUI work |
| --- | --- | --- |
| Connectome Workbench | Downloaded Fit1 in Firefox inside VNC, extracted through the file manager, launched Workbench 1.5.0 through the documented menu, opened the scene with the Scene Files filter and displayed the first group scene. Switched to participant maps 1 (100610) and 5 (105923); also selected participant 105923 in Eccentricity, pRF size and Myelin. | Twelve new captures replace the article’s original screenshot sequence. Numbered click guides added and visually reviewed. |
| FieldTrip | The documented menu opens a terminal with 20211114 loaded. The original article supplies only a placeholder script, so added a clearly labelled example using the public EEG dataset. The data browser opens; segment navigation and time zoom work. | New captures and click guides added. |
| PhysIO | Loaded and ran the Philips ECG3T example through SPM Batch Editor using the current r2021a container and official examples v9.1.0 archive. Inspected the final regressor matrix. Output contains 495 scans and 24 finite regressors. | Current controls and result recaptured; final rendered review remains. |
| SWI | Original calculation completed with CLEAR-SWI 1.7.0. SWI and mIP outputs contain finite values. SWI opened in ITK-SNAP 4.4.0; crosshair navigation works. Fresh viewer screenshot saved. | SWI and mIP both inspected in ITK-SNAP. Refresh the remaining launch and terminal screenshots. |
| Phase unwrapping | ROMEO 4.9.0 completed on the tutorial data and produced a finite 224 by 224 by 160 unwrapped volume. | Compare wrapped and unwrapped images in the GUI and refresh screenshots. |
| MNE EEG | Opened the MNE 0.23.4 container through the desktop menu. Its current launcher is `code 0.23.4`. The bundled MNE conda environment exists and activates after shell initialisation. Public EEG data downloaded successfully. The original analysis code ran in the VS Code GUI with the MNE kernel and Qt plotting, reaching the final frequency spectrum. All five Qt plot windows inspected and recaptured. Time navigation in the EEG viewer verified. Notebook saved through File → Save. | All 13 code cells are saved with execution counts 1–13 and no error outputs; see `mne-gui-execution.txt`. Only the isolated data path was changed. |
| SPM | Completed the full subject08 GUI analysis: Display, CheckReg/Browse, two-run realignment and slice timing, coregistration/contours, segmentation, normalization, smoothing, first-level specification, Review, classical estimation and inference. | New current-platform screenshots replace all remote image references. Final result and complete Satellite Results Table captured. |
| MATLAB | User completed account activation; the R2022a desktop opened. Current FSL wrapper displayed help and an image-copy operation preserved every voxel. Saved keyboard preference verified. | Article and screenshots revised; final rendered review remains. |
| LCModel | Opened LCMgui, selected Varian input, loaded the bundled acquisition and basis, started the analysis and confirmed the voxels. Inspected fitted spectra. All ten voxels produced saved PostScript and table files. | All six article screenshots recaptured cleanly. Numbered click guides added. |

## Confirmed corrections

| Source | Problem | Change and validation |
| --- | --- | --- |
| MNE EEG | Launcher named `vscodeGUI` in the text, while the live menu uses `code`. Download directory case and extraction directory differ from the Python path. | Updated menu label and screenshot. Use one `EEGDemo` directory and an explicit `osfstorage/` source path. The OSF download succeeded in the instance. Added a current-terminal conda initialisation option, verified in the GUI terminal. |
| Connectome Workbench | Open Other defaults to Specification Files, hiding the required scene; the text does not name the filter or nested scene folder. | Explicitly select Scene Files and navigate to `S1200_7T_Retinotopy181/MNINonLinear/fsaverage_LR32k/`. The scene then appears and opens. Added a tested Fit1-only download option, GUI extraction instructions and numbered click guides. Group and individual maps rendered successfully, including all four variable tabs. |
| PhysIO | The original `r7771` launcher is a stub that exits with a maintainer notice: disabled due to a known bug or vulnerability. The current menu only offers `physioGUI r2021a`. | The menu launcher exits without a window or a remaining PhysIO process. In LXTerminal, `ml physio/r2021a` followed by `spm12 fmri` opens SPM12 (12.6). Batch Editor opens and its SPM → Tools menu includes TAPAS PhysIO Toolbox. The direct launch is a verified GUI workaround. The current container has no ECG3T example under `/opt/spm12`; The example URL `https://www.tapas.tnu-zurich.com/examples_v5.0.0.zip` is unreachable from the instance (Firefox connection failure captured). Downloaded the official PhysIO examples v9.1.0 archive from Zenodo record 19075176 in Firefox inside VNC. Extracted and moved it through the file manager. Selected Philips/ECG3T using SPM main Menu → Utils → CD, loaded philips_ecg3t_spm_job.m and ran it with the green Play button. The expected final matrix appeared. multiple_regressors.txt has 495 rows and 24 finite columns; physio.mat and seven quality-control FIG files were saved. Updated the article and captured the current result and controls. |
| fMRIPrep | Comments and whitespace follow continuation backslashes, splitting the example into separate shell commands. | Put each backslash at the end of its line, moved explanation outside the command and included a work directory. CLI options checked against installed fMRIPrep 25.2.7 help. Full processing requires input data and a FreeSurfer license. |
| MRIQC | Broken command continuations and a memory request of 10000 GB. | Corrected continuations and specified 10 GB. Options checked against installed `mriqc/24.0.2`, which reports `24.1.0.dev0+gd5b13cb5.d20240826`. |
| DataLad | `datalad save` follows dataset creation without entering the new dataset. | Added `cd my_dataset` and limited the extension setting to the dataset. OSF publication requires credentials and was not performed. |
| DataLad run | `/storage` does not exist in this platform image. | Use `~/neurodesktop-storage`. Dataset creation, Julia execution, clone and rerun completed and reproduced `hello neurodesktop`. |
| Accessing Neurodesk tools notebook | Saved kernel name `conda-base-py` fails with `NoSuchKernel` under notebook execution. | Changed kernelspec to `python3`; all 11 original code cells then completed. This is separate from the outstanding GUI demonstrations. |
| RISE slideshow | Unclosed JSON fences and a malformed metadata example. | Closed fences and placed `rise` inside the existing `metadata` object. The four code cells completed; slideshow GUI still needs verification. |
| MRSI processing | Nested fences hide commands in the rendered page. | Replaced malformed blocks with Bash fences. Both documented processing entry points exist in `mrsiproc/0.1.0`; complete processing needs acquisition data. |

## Screenshot organisation

Initially reorganized 127 image assets and updated their references. After refreshing MNE, Workbench, PhysIO, FieldTrip and MATLAB, removed 46 superseded, unreferenced captures; their original Git paths are recorded in tutorial-retired-assets.json. Static folders separate branding, supporters, overview guides, contributor screenshots, examples and tutorials. RISE images now live under `static/tutorials/about_neurodesk/rise-slideshow/`. Shared platform screenshots live under `static/tutorials/shared/`. New screenshot filenames use lowercase names with hyphens. The retained-asset move map is [tutorial-asset-moves.json](tutorial-asset-moves.json).

The image checker covers Markdown and notebooks, excludes commented template examples and checks path spelling for case-sensitive deployments. It is included in the image validation workflow.

## Evidence

The files in [tutorial-audit-evidence](tutorial-audit-evidence/) contain the captured command logs. The first module check used the base Python interpreter for MNE and probed an incorrect MRSI command; those results do not establish failures of either GUI application. Later checks identify the MNE `code` wrapper and both actual MRSI entry points. The first isolated CLEAR-SWI run failed because the audit harness used an environment variable that the container did not inherit. Using the tutorial's `homedir()` approach with an isolated directory succeeded; that harness failure is not a tutorial defect.

## GUI test procedure

Use the VNC desktop so its 1280 by 720 proportions remain fixed. Browse and download through Firefox inside Neurodesk. Follow each tutorial in order; record any deviation and the original failing step. Preliminary command and version checks do not count as a completed GUI test.

## Screenshot review status

The screenshots are work in progress. The MNE launch menu now has numbered,
editable SVG click markers, paired with the menu sequence in the text. Raw
captures are retained next to annotated versions. The event, raw EEG, filtered
EEG and evoked-response windows have been inspected and captured at the VNC
aspect ratio. The spectrum and kernel picker have now been recaptured cleanly; the terminal panel is closed in the kernel view. LCModel’s six captures have now been recaptured as isolated dialogs or maximized windows, with numbered controls. The result viewer is scaled to 0.500 so the complete report is visible. The screenshot pass reused the completed results rather than rerunning the analysis.

## Remaining GUI checks

| Tutorial | Next check | Current limitation |
| --- | --- | --- |
| Connectome Workbench | GUI walkthrough completed, including all four participant-map tabs. | Inspect the final numbered overlays and rendered article before publication. |
| SPM | Full GUI walkthrough completed through preprocessing, two-session model, Review, classical estimation and final contrast/results. | Article and all screenshots refreshed; numbered guides reviewed except final model/contrast entries. Final rendered review remains. |
| PhysIO | GUI walkthrough completed with the original Philips ECG3T batch. | Fresh click guides visually reviewed; article requires final rendered review. |
| FieldTrip | Launcher and added raw-data browsing example completed in 20211114. Next-segment and horizontal zoom controls verified. | New screenshots and click guides visually reviewed; article requires final rendered review. |
| MATLAB | User completed MathWorks account activation through the official R2022a activation client, opened directly inside VNC. MATLAB desktop then opened. FSL help and an image operation succeeded with the current wrapper; Windows Default Set selected and persistence verified. | Fresh first-screen activation, desktop, FSL and Preferences captures now replace the nine older images. Article revised with the verified launch and activation workarounds; numbered guides visually reviewed. Final rendered review remains. |
| ROMEO | Load wrapped and unwrapped phase together in ITK-SNAP. | Computation succeeded; comparison GUI remains untested. |
| SWI | Refresh launch, terminal and file selection views, with click markers where useful. | Computation and both result views tested. |
| Accessing Neurodesk tools | GUI walkthrough skipped at the user’s request. | Earlier code checks and kernel correction retained; no GUI completion claimed. |
| RISE slideshow | GUI walkthrough skipped at the user’s request. | Earlier code checks and formatting corrections retained; no GUI completion claimed. |

The other tutorials primarily describe command-line processing, programming or
open-data workflows. Their preliminary checks and text fixes above do not
establish completion of an interactive GUI tutorial.

## Further GUI verification

The remaining tutorials and incomplete GUI steps must be tested before marking this audit complete. Account, data or license requirements should be recorded at the step where they prevent progress, with any available launch or partial results stated separately.

PhysIO completed with non-fatal “Ignoring extra legend entries” warnings in the plotting code; the terminal reports Done and the finite regressor matrix was saved. See `physio-completed-terminal.jpg`.

## FieldTrip added example diagnosis

The original article provides no script or data to reproduce its raw-data browser screenshot. Added browse-eeg.m using the MNE tutorial’s public OSF dataset. The first test script omitted the sub-01/eeg subfolder; that harness path error was corrected. A subsequent header diagnostic showed Fs as [49 50 48 48], because the sample JSON encodes SamplingFrequency as the string "1200". Setting cfg.readbids=false uses the native BrainVision metadata and opens the browser without modifying the dataset. The GUI showed 309 ten-second segments; advancing displayed 10–19.9992 s, and horizontal + shortened the window to about 7.07 s. An attempted history recall selected an unrelated PY line; the full launcher command was then entered explicitly. Neither harness mistake establishes a FieldTrip failure. The tested script differs from the downloadable example only in its isolated audit data path and comments.

## SPM GUI progress

The spm12GUI r7771 menu launches SPM12 (7771) successfully through MCR v97. Selected fMRI, changed working directory through Utils → CD and opened subject 08's anatomy in Display. CheckReg displayed run 1. Following the original Browse instructions literally (Frames 1:146, unfiltered Select All) selected **293 entries**: both 146-volume runs plus the initial frame again. Captured spm-browse-unfiltered-293.jpg. Corrected through bottom-list right-click → Unselect All, Filter `^sub.*run-1_bold`, Frames 1:146, right-list Select All: exactly146 selected. The slider then reached volume101, verified in its image context menu. CheckReg comparison of anatomy and raw functional image shows the expected initial misalignment. Realign (Estimate & Reslice) was selected; its batch is open but not yet configured or run. SPM was minimized during the user’s MATLAB activation and remains paused at this point.

The SPM raw input copy was moved from the audit subfolder to `~/neurodesktop-storage/ds000102/sub-08` to match the tutorial's ordinary working path. The original downloaded DataLad dataset remains in the audit directory. This preparation does not count as a completed GUI preprocessing pipeline. All new SPM screenshots are currently unreferenced pending article updates.

## MATLAB GUI progress

The matlabGUI2022a menu exits without opening activation, and the module exports only `matlab`. Direct MATLAB startup failed with License Manager Error -1 (no license file). Located the official `/opt/matlab/R2022a/bin/activate_matlab.sh` in the container and launched it directly inside VNC with the existing home-to-licenses bind. The user completed MathWorks account activation privately. MATLAB R2022a academic desktop then opened.

The original FSL 6.0.7.4 path resolves to a maintainer-disabled container. Prepending the verified FSL 6.0.7.8_20240913 wrapper directory lets `system('fslmaths')` display help. A real `fslmaths -mul 1` operation returned status0; the 176×256×256 output is finite and preserves every input voxel. Evidence: matlab-gui-checks.txt, matlab-fsl-validation.txt and matlab-fsl-legacy-disabled.jpg. A test command initially lost its first `s` immediately after clc; it was corrected and entered in a separate interaction. This was a harness typing issue, not an application failure.

Preferences → MATLAB → Keyboard → Shortcuts showed Emacs Default Set. Selected Windows Default Set, clicked OK and reopened Preferences to verify it persisted. Fresh current desktop, ribbon, FSL command-window and keyboard-settings screenshots were captured. Reopened the activation client for a blank first-screen capture only; do not repeat activation or record account/license identifiers.

MATLAB article now documents the menu failure, tested direct activation and launch commands, current FSL wrapper and saved keyboard preference. Retired nine superseded captures; no account or license selection screens are published. The initial activation screen was captured and cancelled without repeating activation.

SPM realignment was configured through the GUI with two sessions of 146 raw volumes and default settings. Motion plots span all 292 volumes. The progress and Graphics windows had been minimized, so initially only Batch Editor remained visible; extra Run clicks were issued before identifying the active progress window. Those unnecessary repeats are a test-harness issue, not an SPM failure. Wait for the progress window rather than inferring inactivity from Batch Editor. Slice Timing was then configured in the GUI with two 146-volume realigned sessions, 40 slices, TR2, TA1.95, odd-then-even order and reference1; started once. Fresh first-half SPM captures are now referenced in the article.

SPM checkpoint confirms both rsub and arsub runs are 64×64×40×146 with TR2; both realignment parameter files and the common mean image exist. Coregistration (Estimate & Reslice) used mean run1 as reference and T1 as source. CheckReg of rT1 and mean functional with Contour → Display onto → all shows aligned anatomy. Segmentation was configured with rT1, Save Bias Corrected and Forward fields and started once. The new coregistration and segmentation screenshots replace the corresponding remote images.

Segmentation completed: c1–c5rsub, mrsub and y_rsub anatomical outputs exist. Normalize Write used the forward field and all292 arsub volumes, with default2mm voxels. It completed; CheckReg with first warped run1 volume and the documented avg305T1 template displays aligned images. Graphics was minimized and restored from the middle-click desktop window list. Smoothing was configured for292 warped volumes with default8mm FWHM and started once.

Scope update: the user explicitly requested skipping the Accessing Neurodesk tools and RISE slideshow GUI steps. They are excluded from the remaining work; preliminary notebook checks and text corrections remain documented separately.

Smoothing completed and CheckReg of matching first volumes shows the expected smoother swar image. The first-level model was entered through Batch Editor with both146-scan smoothed runs and all four original12-event schedules (duration2). Saved first-level-job.mat from the GUI before running it. Independent readback in spm-model-validation.txt confirms every onset, duration, timing units/TR and session count. The resulting292×6 matrix has rank6; columns are Inc1, Con1, Inc2, Con2, constant1, constant2. GUI Review of SPM.mat completed. Classical estimation was configured and started once.

SPM final result verified in the GUI with t-contrast Incongruent-Congruent, weights[.5,-.5,.5,-.5], no masking, uncorrectedp.01 and extent10. The contrast editor requires submit before OK; the original article omitted this detail. The MIP and statistics rendered. Opened SPM Figure → Results Table and clicked whole brain to populate a wider Satellite Results Table; this avoids clipping in the narrow fixed-size Graphics window. Numerical readback confirms padded weights[.5,-.5,.5,-.5,0,0], effective residualdf278, six finite beta maps, finite residual/contrast/T maps within the analysis mask, and both finite warped and smoothed79×95×79×146 runs at2mm/TR2. See spm-final-validation.txt. Full SPM GUI test is complete; later final rendering review still required.


## Structural connectivity Neurodesktop rerun — 22 October 2026

Completed the HCP 100307 example in native Neurodesktop terminal and MRview
windows on Neurodesk Play. The 100,000-streamline iFOD2/ACT tractogram and SIFT2
weights from the 21 October processing run were retained. The distributed
anatomy only included an MNI-space aparc+aseg image, which did not match the
T1w-space anatomy used for registration. The tutorial now generates its own
T1w-space cortical and subcortical labels with FreeSurfer 7.4.1 SynthSeg 2.0
(`--parc --cpu --threads 8`) from the supplied brain-extracted T1w image. This
change is stated explicitly: it is not the original surface-based HCP
FreeSurfer reconstruction.

SynthSeg completed, followed by labelconvert, the inverse T1w-to-diffusion
header transform, and SIFT2-weighted tck2connectome with symmetric,
zero-diagonal, inverse-node-volume scaling. The parcellation overlay was
inspected in MRview's three-plane view. The Python matrix plot opened in a
native desktop window. All eleven article screenshots are native window
captures; the final three show connectome construction, node alignment and
the matrix. PNG optimisation is lossless.

Numerical checks: tckinfo reports exactly 100,000 streamlines, and there are
100,000 finite, nonnegative SIFT2 weights. The output matrix is 84 by 84,
finite, nonnegative, symmetric and zero-diagonal, with 1,499 nonzero undirected
edges. These are consistency checks for this teaching run, not validation of
biological connectivity. Processing timestamps, normalized command output,
SynthSeg QC, tractogram metadata and numerical checks are retained under
`structuralconnectivity-2026-10-22/`. Terminal progress escape codes and
intermediate percentage updates have been removed from the saved text logs.


## Structural connectivity screenshot style follow-up — 22 October 2026

Compared the FreeSurfer and FieldTrip GUI guides with the structural connectivity
page. Recaptured the four MRview checks with their actual ODF display, Overlay
and Tractography panels visible. Added the repository's editable green numbered
SVG markers and matching numbered instructions. The unmarked PNGs remain beside
the guides. FOD glyph scale is 4; the tractography panel shows direction colours
and a 2.5 mm slice slab; the node overlay has Interpolate disabled. Corrected
`-mode 1` to `-mode 2` for the three-plane MRview commands (F2 in the GUI).
The completed 100,000-streamline analysis and matrix are unchanged.
