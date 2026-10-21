---
title: Structural connectivity dMRI
linkTitle: Structural connectivity dMRI
weight: 1
aliases:
- /tutorials/structural_imaging/structuralconnectivity
description: 'Build a single-subject diffusion MRI structural connectome with MRtrix3 in Neurodesk.'
authors:
- name: Joan Amos
- name: Michèle Masson-Trottier
date: '2026-10-21'
---
# Structural connectivity from diffusion MRI

:::{admonition} Learning Objectives
:class: tip

By the end of this tutorial you will be able to:

- Prepare anatomical and diffusion inputs from the HCP 100307 example.
- Run an MRtrix3 tractography and connectome workflow in Neurodesk.
- Inspect the resulting connectivity matrix.
:::

This example follows one HCP subject through a standard MRtrix3 workflow. It uses 100,000 streamlines so the example is practical to run; increase that number only when you have enough time and storage for a larger tractogram.


[Getting Set Up with Neurodesk](https://neurodesk.org/getting-started/)

## 1. Prepare the data

Download the subject 100307 files from the linked [structural archive](https://drive.google.com/file/d/1bj-Tz2xLGn0L05CveOYnzTgkewc_IU5F/view) and [diffusion archive](https://drive.google.com/file/d/193ZaUmXbT59IoXoAJ-Y1pf_wgdSHdKpR/view). Extract both into a folder on Neurodesk storage. Keep the HCP directory structure intact. The subject folder should contain:

```text
100307/
├── MNINonLinear/
├── T1w/
│   ├── Diffusion/
│   │   ├── bvals
│   │   ├── bvecs
│   │   └── data.nii.gz
│   ├── T1w_acpc_dc_restore_brain.nii.gz
│   └── 100307/aparc+aseg.nii.gz
```

The parcellation must be in the same T1w space as the anatomical image. Do not substitute `MNINonLinear/aparc+aseg.nii.gz`; it is in a different space. If the structural archive does not include `T1w/100307/aparc+aseg.nii.gz`, download the HCP Structural Extended data for subject 100307.

Open a Neurodesk terminal and load MRtrix3 and FSL. Change `/data/your-folder/100307` to the subject folder you created:

```bash
ml mrtrix3/3.0.3 fsl/6.0.5.1
cd /data/your-folder/100307
mkdir -p mrtrix-results
cd mrtrix-results
```

The screenshot shows the current Neurodesk desktop terminal checking the HCP diffusion image header. It confirms that the image is available and contains 288 volumes at 1.25 mm resolution.

![MRtrix3 checking the HCP 100307 diffusion input in Neurodesk](/static/tutorials/structural_imaging/structuralconnectivity/01-mrtrix-input.png)

## 2. Prepare diffusion and anatomy images

MRtrix reads the compressed NIfTI directly, so there is no need to expand `data.nii.gz` into a multi-gigabyte file. Convert the image and import its FSL gradient table:

```bash
mrconvert ../T1w/Diffusion/data.nii.gz DWI.mif \
  -fslgrad ../T1w/Diffusion/bvecs ../T1w/Diffusion/bvals \
  -datatype float32 -stride 0,0,0,1

dwibiascorrect ants DWI.mif DWI_bias.mif -bias bias.mif
dwi2response dhollander DWI_bias.mif response_wm.txt response_gm.txt response_csf.txt
dwi2mask DWI_bias.mif DWI_mask.mif
dwi2fod msmt_csd DWI_bias.mif \
  response_wm.txt wmfod.mif response_gm.txt gm.mif response_csf.txt csf.mif \
  -mask DWI_mask.mif
mtnormalise wmfod.mif wmfod_norm.mif gm.mif gm_norm.mif csf.mif csf_norm.mif \
  -mask DWI_mask.mif
```

Create a five-tissue-type (5TT) image from the brain-extracted T1w image, then register its grey-matter volume to the diffusion mean b=0 image. The transform will later align both the 5TT image and the parcellation with diffusion space.

```bash
5ttgen fsl ../T1w/T1w_acpc_dc_restore_brain.nii.gz 5TT.mif -premasked
dwiextract DWI_bias.mif - -bzero | mrmath - mean mean_b0.mif -axis 3
mrconvert mean_b0.mif mean_b0.nii.gz
mrconvert 5TT.mif 5TT.nii.gz
fslroi 5TT.nii.gz 5TT_gm.nii.gz 0 1
flirt -in mean_b0.nii.gz -ref 5TT_gm.nii.gz -dof 6 -omat diff2struct_fsl.mat
transformconvert diff2struct_fsl.mat mean_b0.nii.gz 5TT_gm.nii.gz \
  flirt_import diff2struct_mrtrix.txt
mrtransform 5TT.mif -linear diff2struct_mrtrix.txt -inverse 5TT_coreg.mif
5tt2gmwmi 5TT_coreg.mif gmwmSeed_coreg.mif
```

## 3. Generate and filter a tractogram

Generate a 100,000-streamline iFOD2 tractogram using grey–white matter interface seeding and anatomical constraints, then estimate a SIFT2 weight for each streamline:

```bash
tckgen wmfod_norm.mif tracks_100k.tck \
  -algorithm iFOD2 -act 5TT_coreg.mif -backtrack -crop_at_gmwmi \
  -seed_gmwmi gmwmSeed_coreg.mif -maxlength 300 -select 100000 -nthreads 4

tcksift2 tracks_100k.tck wmfod_norm.mif sift2_weights.txt \
  -act 5TT_coreg.mif -out_mu sift2_mu.txt -nthreads 4
```

The tractogram size and run time depend on available Neurodesk resources. For a quick test, lower `-select` (for example, to `10000`). Use a larger value for a research analysis and report it with the other processing settings.

## 4. Build the connectome

Convert the Desikan–Killiany parcellation to MRtrix node labels, transform it into diffusion space, and build a symmetric, SIFT2-weighted matrix. The lookup tables are supplied by the FreeSurfer and MRtrix3 installations; adjust these paths if your loaded module versions use different locations.

```bash
FREESURFER_LUT=/opt/freesurfer-7.2.0/FreeSurferColorLUT.txt
MRTRIX_LUT=/opt/mrtrix3-3.0.3/share/mrtrix3/labelconvert/fs_default.txt

labelconvert ../T1w/100307/aparc+aseg.nii.gz \
  "$FREESURFER_LUT" "$MRTRIX_LUT" nodes.mif
mrtransform nodes.mif -linear diff2struct_mrtrix.txt -inverse \
  -datatype uint32 nodes_coreg.mif
tck2connectome tracks_100k.tck nodes_coreg.mif connectome.csv \
  -tck_weights_in sift2_weights.txt -symmetric -zero_diagonal \
  -scale_invnodevol -out_assignments assignments.txt
```

Open `connectome.csv` in MATLAB to inspect the matrix:

```matlab
connectome = readmatrix('connectome.csv');
imagesc(connectome);
axis square;
colorbar;
title('HCP 100307 SIFT2-weighted connectome');
xlabel('Region');
ylabel('Region');
```

Check image alignment in MRtrix before interpreting the matrix. A parcellation that is shifted or in a different space will produce misleading node assignments. For multi-subject or publication analyses, consult the references and report the complete preprocessing and tractography settings.

## References

- [MRtrix3: structural connectome for the Human Connectome Project](https://mrtrix.readthedocs.io/en/3.0.8/tutorials/hcp_connectome.html)
- [MRtrix3: structural connectome construction](https://mrtrix.readthedocs.io/en/3.0.8/quantitative_structural_connectivity/structural_connectome.html)
- [HCP S1200 data directory structure](https://www.humanconnectome.org/storage/app/media/documentation/s1200/HCP_S1200_Release_Appendix_III%2B7T%2BDiffBed.pdf)
