# Neurodesk GUI tutorial audit

20 October 2026 · Neurodesk Play America · Neurodesktop 2026-10-07 · Ubuntu 24.04.5 LTS

The initial revision (`d396631d`) completed nine GUI walkthroughs. Follow-up revisions are in progress; the status below describes that initial revision.

Nine GUI walkthroughs were completed in the VNC desktop. Websites and downloads were used through Firefox inside Neurodesk. Tests followed the published steps first; necessary corrections and deviations are listed below. The Jupyter tools and RISE slideshow GUI checks were explicitly skipped at the user's request.

## Completed GUI walkthroughs

| Tutorial | Verified result | Main correction |
| --- | --- | --- |
| Connectome Workbench | Workbench 1.5.0 opened the Fit1 scene; group and participant 105923 maps displayed across Polar Angle, Eccentricity, pRF size and Myelin. | Specify the nested scene directory and Scene Files filter. Added the smaller Fit1-only download and GUI extraction steps. |
| MNE EEG | All 13 analysis cells ran in the VS Code GUI using MNE 0.23.4 and Qt plotting. Raw, events, filtered, evoked and spectrum windows inspected; time navigation tested; notebook saved. | Current menu is `code 0.23.4`. Corrected data directory case/path, explicit OSF source path and conda initialisation. |
| FieldTrip | 20211114 data browser opened 309 ten-second segments. Next-segment and horizontal zoom controls worked. | Original article had only a placeholder script. Added a downloadable public-data example. `cfg.readbids=false` avoids the sample JSON's string SamplingFrequency being interpreted as ASCII values. |
| PhysIO | Original Philips ECG3T batch ran through SPM Batch Editor. Final matrix contains 495 rows and 24 finite regressors; physio.mat and seven quality-control figures saved. | Old r7771 container is disabled; current menu silently exits. Direct `ml physio/r2021a` then `spm12 fmri` works. Replaced the unreachable example archive with official PhysIO examples v9.1.0 from Zenodo. |
| LCModel | LCMgui loaded bundled Varian data and basis, ran the analysis and displayed fitted spectra. All ten voxels produced PostScript and table files. | Replaced all six screenshots with clean current dialogs/results and numbered click targets. |
| MATLAB | User activated R2022a privately; desktop opened. Current FSL wrapper returned help and performed a real image operation. Output is finite and preserves every voxel. Windows Default Set persisted after reopening Preferences. | Menu launcher exits; documented direct launch/activation. FSL 6.0.7.4 is disabled; prepend the current 6.0.7.8 wrapper directory. |
| SPM | Full subject08 analysis: Display, CheckReg/Browse, realignment, slice timing, coregistration/contours, segmentation, normalization, smoothing, two-session first-level model, Review, estimation and final contrast/results. | Unfiltered Browse selected 293 entries instead of one 146-volume run. Added filtering and clearing the selection. Added contrast `submit` and the wider Satellite Results Table procedure. |
| SWI | Downloaded/extracted data, saved the original Julia recipe in Nano, launched CLEAR-SWI 1.7.0 through the menu and ran it. Opened both outputs in ITK-SNAP 4.4.0 and compared tiled views. | Added Nano function-key alternatives, explicit image wizard steps, tiled-layout control and automatic contrast adjustment. |
| Phase unwrapping | Menu-launched ROMEO 3.2.8 processed the normal `romeo-demo` folder. `unwrapped.nii` and settings file created; wrapped and unwrapped images compared in ITK-SNAP 4.4.0. | Added exact output filename, Add Another Image, tiled layout and a reproducible -10 to 10 display window. With nomask, automatic contrast is dominated by background noise. |

## SPM numerical verification

Both runs contain 146 volumes. Realigned/slice-timed images are 64×64×40×146 with TR 2 s. Normalized and smoothed images are finite 79×95×79×146 arrays at 2 mm. All original condition onsets and durations were read back from the GUI-saved batch. The design matrix is 292×6, rank 6, with columns Inc1, Con1, Inc2, Con2, constant1, constant2. The original four contrast weights are correct: SPM pads them to [.5,-.5,.5,-.5,0,0]. Residual degrees of freedom: 278. All beta, residual, contrast and T values are finite inside the analysis mask. Final inference used no masking, uncorrected p .01 and extent 10.

## Failures and fixes

The reproducible tutorial failures were the PhysIO and MATLAB menu launchers, disabled legacy PhysIO/FSL containers, the obsolete PhysIO download, MNE launch/path/environment instructions, SPM's ambiguous file selection and FieldTrip's missing runnable example. Updated instructions and screenshots now show the tested routes. MATLAB activation was completed by the user; no account or license details appear in teaching screenshots. Network-license activation remains untested.

PhysIO emitted non-fatal “Ignoring extra legend entries” plotting warnings and still completed with the expected matrix. SPM's minimized progress/Graphics windows initially prompted unnecessary repeat Run clicks during testing; this was an automation issue, not an application defect. A CLEAR-SWI diagnostic initially used an environment variable that the container did not inherit; the tutorial's homedir() recipe worked. A browser input timeout interrupted one ROMEO preparation command before execution; it was cancelled and re-entered in a clean terminal.

## Scope and other tutorials

| Tutorial(s) | Status and limits |
| --- | --- |
| Accessing Neurodesk tools; RISE slideshow | GUI checks skipped by user. Earlier notebook code checks passed (11 and 4 cells respectively). Fixed the tools kernelspec and RISE Markdown/metadata examples. These checks do not establish GUI completion. |
| fMRIPrep; MRIQC | Menu launches captured; repaired shell continuations and MRIQC's 10000 GB request to 10 GB. Installed CLI options checked. Full processing not run; requires appropriate BIDS input and, for fMRIPrep, a FreeSurfer license. |
| DataLad; DataLad run | Corrected dataset directory/local setting and obsolete /storage path. Create, run, clone and rerun checked. OSF publication not performed. |
| MRSI processing | Repaired malformed code fences; both installed processing entry points found. Full processing not run because acquisition data were not supplied. |
| PhysIO batch scripting | Separate scripting guide requires the author's acquisition data and helper functions. Its complete batch workflow was not run; the Philips GUI example above was tested independently. |
| Structural connectivity; FreeSurfer; MFCSC | Primarily command-line processing guides. Full pipelines and their output screenshots were not rerun in this GUI-focused pass. Their relocated images are retained originals, not refreshed captures. |
| Conda; MyST; OSF client | Programming/documentation/open-data guides; no complete interactive GUI walkthrough claimed. |

## Screenshots and assets

Initially reorganized 127 images into branding, supporters, guides, contribute, shared platform and per-tutorial folders. 60 superseded original captures were retired after replacing their references; original Git paths are recorded in [tutorial-retired-assets.json](tutorial-retired-assets.json). Retained moves are recorded in [tutorial-asset-moves.json](tutorial-asset-moves.json).

There are 56 editable, self-contained SVG click guides. Genuine VNC captures sit beside their annotated versions. Markers identify controls without recreating application content. Teaching images use isolated dialogs or application windows and omit browser chrome/taskbar where possible. MNE's kernel list is cropped from the genuine capture to exclude temporary audit paths; the full capture remains in evidence. New screenshot names use lowercase words separated by hyphens. Original screenshot proportions are preserved.

The asset validator checks Markdown and notebook references, including exact case for Linux deployment, and runs in the image-validation workflow. It excludes commented template examples and runtime image display calls.

## Evidence and validation

[tutorial-audit-evidence](tutorial-audit-evidence/) contains command logs, GUI result checks, the Nano-saved Julia script and diagnostic screenshots. The preserved work journal is chronological and contains interim states superseded by this report. Only the completed results above describe final GUI status.

Initial revision checks passed:

- Website build: 99 pages and 100 legacy redirects.
- Publication verifier: all 99 pages, raw source downloads, saved notebook cells and redirects verified.
- Existing build tests: 26 run, one optional integration test skipped; no failures.
- Existing notebook-image validator tests: seven passed.
- Source image checks: 147 Markdown/notebook references; no missing or case-mismatched paths. The older notebook checker separately checked 37 references in 57 source notebooks.
- Browser review: all nine refreshed tutorial pages loaded their images without errors; numbered guides and phase viewer sections visually inspected.
- Asset maps: all 77 retained destinations exist; all 60 retired originals are recoverable from Git; all 56 click-guide source captures exist.
- Git whitespace check passed.

The older notebook-image checker also scans generated notebooks when passed all of books/. After a local build, run it against books/tutorials and books/examples to avoid reporting obsolete/generated source copies. CI starts from a clean checkout.

Implementation branch: `tutorial-platform-audit-2026-10-20`. The GUI results above describe the tested revision; deployment status is tracked separately in its pull request.


## Follow-up revision: shared media and clearer launch instructions

Reusable screenshots now live only in [neurodesk/media](https://github.com/neurodesk/media/tree/main/screenshots/neurodesk), merged through [media PR #1](https://github.com/neurodesk/media/pull/1). Tutorials link to the canonical main-branch PNGs. The migration map in [shared-media-migration.json](shared-media-migration.json) records replaced paths; the earlier asset-move map follows these moves through to their current destinations. Replaced copies, including duplicate fMRIPrep/MRIQC launcher images, have been removed from this repository.

The shared library has 21 images: a clean launcher with separate desktop, terminal and notebook guides; a clean desktop and terminal; numbered software-menu guides; and reusable SPM controls. Fresh menu captures cover fMRIPrep 25.2.6, MRIQC 24.0.2, PhysIO r2021a, SPM r7771, MATLAB 2022a and LCModel 6.3. Menu instructions and marker numbers agree. A menu capture establishes the available entry, rather than successful analysis.

All 23 tutorial sources now include a revision date and Michèle Masson-Trottier as an author alongside the original authors. Learning objectives have been added where relevant; the phase tutorials retain their existing objectives and have simpler opening formatting. The tools and RISE GUI checks remain skipped.

Public dataset preparation was rerun in the VNC terminal: `datalad clone https://github.com/OpenNeuroDatasets/ds000102.git`, then `datalad get sub-08/`, both completed. The clone is under `~/neurodesktop-storage/open-data/ds000102`. Current BIDS validation rejects the dataset's optional bare `CogAtlasID` value. The original JSON was backed up outside the dataset and the optional key removed from the working copy; validation then continued with a missing SliceTiming warning. A complete fMRIPrep run is still being debugged, including the container's default missing SUBJECTS_DIR. No successful fMRIPrep result is claimed at this stage.

FreeSurfer 8.2.0 was checked for a readable bundled license and bundled fsaverage demonstration files; no license contents were read or published. Freeview opens. The expanded GUI example and new output captures are in progress.

The media repository's asset and PR-size checks pass. All shared image targets resolve locally and the published main-branch URLs return HTTP 200. The refreshed sources have no missing local image references. Remaining GUI/example revisions from the feedback are not marked complete by these checks.
