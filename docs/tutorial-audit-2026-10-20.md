# Neurodesk GUI tutorial audit

20 October 2026 · Neurodesk Play America · Neurodesktop 2026-10-07 · Ubuntu 24.04.5 LTS

The initial revision (`d396631d`) completed nine GUI walkthroughs. The completed-walkthrough table describes that initial revision; the scope table and dated follow-up sections include subsequent work.

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
| fMRIPrep | Menu captured and input preparation tested. Full processing remains unverified; see the follow-up notes below. |
| MRIQC | Public ds000102 T1w example completed, with 68 finite numerical metrics. Report inspected in Firefox and captured; loaded-terminal screenshot added. |
| DataLad; DataLad run | Corrected dataset directory/local setting and obsolete /storage path. Create, run, clone and rerun checked. OSF publication not performed. |
| MRSI processing | Corrected Part 2 option parsing; both template syntax checks passed. Added preparation screenshots. Full processing and result screenshots await compatible acquisition data or completed Part 1 outputs. |
| PhysIO batch scripting | Separate scripting guide requires the author's acquisition data and helper functions. Its complete batch workflow was not run; the Philips GUI example above was tested independently. |
| Structural connectivity | Full pipeline and output screenshots have not been rerun. Retained images are originals. |
| FreeSurfer | Freeview fsaverage GUI walkthrough completed, including segmentation overlay and surface controls. Fresh startup screenshot now shows the open application. Reconstruction was not run. |
| MFCSC | All 50 public FC–SC pairs processed and compared with published reference outputs. Diagnostic figures and result report captured; non-finite values documented. |
| Conda; MyST; OSF client | Programming/documentation/open-data guides; no complete interactive GUI walkthrough claimed. |

## Screenshots and assets

Initially reorganized 127 images into branding, supporters, guides, contribute, shared platform and per-tutorial folders. 60 superseded original captures were retired after replacing their references; original Git paths are recorded in [tutorial-retired-assets.json](tutorial-retired-assets.json). Retained moves are recorded in [tutorial-asset-moves.json](tutorial-asset-moves.json).

The initial revision contained 56 editable, self-contained SVG click guides. Genuine VNC captures sit beside their annotated versions. Markers identify controls without recreating application content. Teaching images use isolated dialogs or application windows and omit browser chrome/taskbar where possible. MNE's kernel list is cropped from the genuine capture to exclude temporary audit paths; the full capture remains in evidence. New screenshot names use lowercase words separated by hyphens. Original screenshot proportions are preserved.

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


### FreeSurfer GUI example

FreeSurfer 8.2.0 / Freeview was opened from LXTerminal. The bundled fsaverage `T1.mgz`, `aparc+aseg.mgz` and `lh.pial` were loaded through the File menu. Lookup-table colours, visibility, opacity 0.35 and Cursor structure labels were checked; label 51 read Right-Putamen. Single View, 3D view, cursor/frame hiding and mouse rotation worked. The tutorial now provides these complete GUI steps instead of a reconstruction-only recipe. Seven canonical Freeview images are on the media follow-up branch `neurodesk-shared-gui-controls-2026-10-20`; raw working captures are not duplicated in the repositories.

### MRIQC open-data example

MRIQC's menu entry 24.0.2 reports executable version `v24.1.0.dev0+gd5b13cb5.d20240826`. A T1w-only participant-08 run on the downloaded ds000102 dataset completed successfully in 6 minutes 4 seconds, with `--no-sub --notrack`. It produced `sub-08_T1w.html` and 68 finite numerical metrics in `sub-08/anat/sub-08_T1w.json`. Example values were SNR total 6.02006, CNR 2.26143 and EFC 0.4384. The same command completed from the menu-opened terminal in 49 seconds using its work cache. The HTML report was opened in Firefox inside VNC; its background and anatomical mosaic panels were inspected and captured. Execution and finite-metric checks are saved in the evidence folder.

The first metadata revision introduced a duplicate MyST frontmatter block and repeated older author/date lines in the tools and RISE notebooks. Those have been consolidated, retaining the original author's ORCID, affiliations and license. Phase notebooks retain their original MIT license in frontmatter. These edits do not change the skipped GUI-test status.


### Shared-image publication

The MyST exporter normally copies remote screenshots into hashed PNG/WebP assets. The publisher now restores direct `neurodesk/media` URLs in rendered HTML and client-navigation article data, removes the local picture alternatives and deletes those copied assets. This keeps one canonical published screenshot and lets media updates propagate without rebuilding each consuming page. Raw source downloads remain unchanged. Two regression tests cover HTML, navigation data, preserved unrelated assets and source downloads, and JSON property ordering. All 28 build tests pass (one optional integration fixture skipped); a real 99-page build linked 27 shared screenshots directly. Browser checks confirmed that the Freeview images load from the media URLs after hydration.

Duplicate body author/date lines were removed because the site already renders that information from frontmatter. Each tutorial retains its author list and revision date in the standard page header.

### Formatting review — 21 October 2026

Checked all 99 exported pages in the local browser and the publication validator. Separated 18 screenshot/caption pairs across Accessing Tools, SWI and ROMEO so shared screenshots render at reading width. The publication adapter removes 10 empty headings and promotes two titles that previously appeared twice, while preserving the source notebooks and saved code outputs. Fixed contribution-page link markup and literal GitHub/package names being parsed as citations.

Inline code now uses the Neurodesk logo palette: dark green on light backgrounds and light green on dark backgrounds; fenced-code syntax highlighting is retained. Published custom stylesheets have a content version so refreshed previews pick up the change. Added layout regression checks; 31 build tests pass with one optional integration test skipped. The page-by-page browser results are in `tutorial-audit-evidence/formatting-check-2026-10-21.json`. These are formatting checks, not additional workflow execution claims.

### GUI feedback revision — 21 October 2026

- Replaced the FreeSurfer introduction's generic empty terminal with Freeview fully opened. Added the actual MRIQC-loaded terminal and made both terminal references explicit.
- Regenerated shared PNG click guides and tutorial SVG annotations in the Neurodesk green palette. Launcher rectangles now match the tile bounds; number glyphs are geometrically centred. Reusable OSF folder-download controls are stored once in the media library.
- Re-ran FieldTrip from a fresh 157 MB OSF download in `~/neurodesktop-storage/EEGDemo`. Downloaded `browse-eeg.m` through GitHub's Download raw file button in Firefox inside VNC, ran it from the menu-launched 20211114 terminal, opened segments 1 and 2 of 309 and tested horizontal zoom (approximately 7.07 seconds, 437 segments). Added preparation, launch and intermediate-view screenshots.
- Ran MFCSC 1.1 on all 50 public FC–SC pairs, 84 regions each. The installed build writes `mask.csv`, selects 1,009 ipsilateral connections and opens diagnostic figures until Enter is pressed. Compared all output matrices with the OSF reference: identical masks and NaN locations; maximum finite difference approximately 0.00001, all 50 pairs agree within absolute tolerance 0.000011.
- MFCSC QC found 15 selected non-finite values in eight participants, all at zero SC entries. The same locations occur in the published reference. The companion checker retains the original outputs, excludes non-finite/sentinel values and writes a common valid mask with 998 connections. The Firefox report and terminal check are genuine outputs of this run. See `tutorial-audit-evidence/mfcsc-result-check.txt`.
- MRSIProc 0.1.0's installed Part 2 parser is `o:d:s:n:f:a:l:k:r:N:SuRwbq?`: `-S` takes no argument. The original metabolite-list operand halts option parsing, leaving `-N`, `-R` and `-b` unprocessed. Corrected the template to argument-free flags and an absolute Part 1 results path. `-N Both` retains MINC outputs while adding NIfTI. Verified the installed parser and both template syntax checks; the Neurodesk module function is available in a child Bash shell.
- **MRSI end-to-end execution remains pending:** no compatible raw acquisition or completed Part 1 results folder was found. Requested a de-identified folder path or public demo from the user. Added genuine Mousepad preparation and terminal syntax-check images, labelled the page's verification status, and retired its unverified legacy screenshots. No reconstruction, Part 2 map generation or MRSI result screenshot is claimed.

The revised shared screenshots currently use the media follow-up branch so the local preview displays the new green guides before that media PR is merged.

Latest validation: the rebuilt site publishes 99 pages and 100 redirects; publication/layout checks and all 136 local image references pass. All 31 build tests pass with one optional integration fixture skipped. The five revised pages load all 35 teaching images in the local browser. Shared guides are proposed in [media PR #2](https://github.com/neurodesk/media/pull/2); its naming, format and size checks and PR-size budget pass.

### Public MRSI example-data search — 21 October 2026

The Vienna [raw-spectrum example](https://zenodo.org/records/3904584) and [volunteer map release](https://zenodo.org/records/5006923) currently require individual access approval. The open CC BY 4.0 [DeuteriumToProtonExchangeMRS v1.0 archive](https://zenodo.org/records/5705959) is 3.9 GB. Its full ZIP directory (108,849 entries) contains processed MRSI maps, fitting tables and basis sets, but no MRSI coordinate files or complete Part 1 metadata folder. Its 68 coordinate files belong to the separate SVS analysis. This archive can support viewing published maps, but does not establish an unchanged Part 2 processing example.

The official [FSL-MRS MRSI practical](https://pages.fmrib.ox.ac.uk/fsl/fsl_mrs_practicals/ch4_mrsi_fitting.html) offers spectra, anatomy, a mask, a basis set and prepared results for a separate FSL-MRS exercise. Its download was not tested in Neurodesk; switching to that workflow would require a separately labelled tutorial. No compatible MRSIProc end-to-end demo was verified. See `tutorial-audit-evidence/mrsiproc-public-data-search.json`.

### Native screenshot quality and branch update — 21 October 2026

The recent small captures were taken from an 806-pixel browser-scaled VNC canvas and saved as JPEGs. Converting those files to PNG would not recover the missing detail. They are being replaced by fresh 1280-pixel PNGs captured from the actual 1280 × 720 X11 desktop, excluding the taskbar. Original screenshot bytes are exported through JupyterLab's image viewer; no upscaling or simulated application content is used. Shared launcher/control images remain in `neurodesk/media`; analysis-specific images remain with their tutorials. The green click-guide renderer now saves full-colour PNGs without palette quantisation.

MyST also generates lossy WebP alternatives. The publication adapter now preserves original tutorial PNGs in initial HTML and client-navigation JSON. A regression test covers both routes and preserves unrelated images and raw source downloads. The publisher suite passes: 31 tests pass and one optional fixture is skipped.

PR #213 was already merged before the last two audit commits. The follow-up branch `tutorial-gui-follow-up-2026-10-21` contains those commits and merges the latest `origin/main` sidebar fix without conflicts. The media follow-up PR #2 is current with main and its new native captures pass asset checks and the 5 MiB PR budget.

### FSL-MRS public-data example — 21 October 2026

The user selected the FSL alternative after the MRSIProc dataset search. The official practical's GitLab download timed out inside Neurodesk Firefox. The authors' [FSL-MRS 2.1.0 archive](https://zenodo.org/records/7956237) downloaded successfully in Firefox inside VNC. Its `example_usage/example_data/example_mrsi` folder includes the reconstructed MRSI grid (48 × 48 × 1 × 1024), water reference, a 96-voxel mask, matching basis spectra and a prepared T1 anatomical folder.

FSL 6.0.7.23 provides FSL-MRS 2.4.16 and FSLeyes 1.20.1 with the MRS plugin. The input spectrum displays correctly at world coordinates approximately (0, 0, 42.67385); the default anatomical slice was outside the spectroscopy plane. Tissue-fraction generation succeeded.

The four-worker fit reached 100% in 9 minutes 7 seconds, but failed in `client.close()` before saving maps. The Python 3.14 / distributed / Bokeh shutdown traceback ends in `RuntimeError: Cannot synchronously wait on a running event loop; use 'await stop_async()'`. Only `fit_avg.png` existed after that attempt. The new script uses `--parallel off` to avoid this dependency path and the current `--baseline poly,2` syntax. The serial run and its saved outputs are checked separately below; the parallel progress bar is not counted as success. This is a separate FSL-MRS example, not a claim that FSL outputs can be passed to MRSIProc Part 2.

The native recaptures replace all 16 recent scaled tutorial images (six FieldTrip, seven MFCSC and three MRSIProc preparation images) and four shared media images. All 52 annotation source dimensions match their image files. FieldTrip was rerun from a new archive download; segments 1/309, 2/309 and the shorter 2/437 time window were captured after drawing completed. MFCSC's repeat run exited normally after Enter and supplied a fresh participant-fit capture.

The quality preview rebuilt 99 pages and 100 redirects. Browser checks covered all 99 pages and 410 article images: no failed images, visible empty headings or page-width overflow. An apparent empty-heading issue in an embedded MRIQC report was verified to consist of zero-height accordion placeholders. All 51 published tutorial PNGs are pixel-identical to their sources after lossless recompression. Client-side navigation into MFCSC also retains the original 1280-pixel PNGs. Page-check evidence is saved in `tutorial-audit-evidence/screenshot-quality-pages-2026-10-21.json`.

The serial FSL-MRS run completed successfully in 38 minutes 56 seconds and saved 222 NIfTI files under `concs`, `fit`, `misc`, `nuisance`, `qc` and `uncertainties`, plus an HTML report. The input mask is two-dimensional (48 × 48); the maps retain a singleton third spatial dimension. The checker applies that mask to the first two spatial axes, verifies affine agreement and checks all 315,936 selected values across the map and spectral outputs. None are non-finite. The internally referenced NAA+NAAG map ranges from 0.90157 to 1.69681 (mean 1.31356). See `tutorial-audit-evidence/fsl-mrsi-result-check.json` and the checking script beside it. Finite values establish output integrity, not biological validity of the concentration estimates.

FSLeyes loaded the saved fit through Tools → Load MRSI fit. The measured spectrum, model prediction, baseline and residual display at voxel [23, 23, 0]. The MRSI map panel selects NAA+NAAG / conc-internal. The example uses display limits 0.9–1.7 and clips background zeros at 0.001; the four spectral image planes are hidden in the left overlay list while their curves remain plotted. Restoring and maximising the window refreshed initially incomplete map-control painting. Native PNG captures document the download, inputs, spectrum, load-fit menu, completed outputs, fitted spectrum, range settings and final map. The tutorial remains separate from the MRSIProc reference workflow.

Final validation: 100 published pages, 101 redirects and 144 local image references pass the publication checks. The combined browser check covers all 100 pages and 418 article images, with no failed images or page-width overflow. All 54 published tutorial PNGs are pixel-identical to their sources; all 55 annotation source dimensions match. The FSL page was also checked after following its link from MRSIProc.

Publication follow-up: cached executed notebooks previously replaced the entire current source, bringing back obsolete titles, screenshots and instructions. Publication now copies only outputs and widget state when the complete code-cell sequence matches, preserving current Markdown and metadata. Regression checks cover changed code and widget state. The image postprocessor also removes unused picture wrappers when removing WebP alternatives, keeping server HTML consistent with React's lossless image rendering. Stylesheet URLs stay identical to the serialized client data. Browser CI additionally opens the FSL-MRS example and checks all eight native-width images.

Author and asset ownership follow-up: published headers own the author list and date. Redundant author/date lines are removed from the staged leading Markdown when the same metadata is in the header, preserving source downloads, licence notices, citations and fenced code. Seven example-specific images moved from media to EDU: six fsaverage/Freeview walkthrough images and the MFCSC OSF input-folder download. Their pixels are unchanged and their raster annotation definitions moved with them. Generic launchers, menus and empty application controls remain in media. A SHA-256 scan found no identical screenshots in both media/screenshots and EDU books/static.

MNE quality correction — 21 October 2026: the preceding quality pass missed MNE's 850–896-pixel JPEGs and its 420 × 60 kernel crop. The current build was serving those files; this was not a stale-page explanation. Reopened the tested notebook in the MNE 0.23.4 GUI, prepared a clean copy at `/home/jovyan/neurodesktop-storage/EEGDemo/EEGDemo.ipynb` and reran all 13 code cells. Saved execution counts are 1–13 with no error outputs; the GUI kernel label is `mne-0.23.4 (Python 3.9.7)`. Captured each of the five actual result windows separately, maximised, from the native VNC desktop. Also captured the notebook code cell, the complete kernel menu, the activated integrated terminal and the four-level application menu. All nine replacements are 1280-pixel original PNG captures, with the taskbar excluded. The generic launcher remains in media; the eight example-specific captures remain in EDU. New full-context green guides replace the kernel crop and identify the code cell, run button and shell terminal. The page states which code belongs in each interface.
