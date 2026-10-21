from pathlib import Path
import json
import numpy as np
import nibabel as nib
import fsl_mrs

work = Path.home() / 'neurodesktop-storage/fsl-mrs-demo/fsl_mrs-2.1.0/example_usage'
output = work / 'MRSI/fsl_mrsi_fit'
mask_image = nib.load(work / 'example_data/example_mrsi/mask.nii.gz')
mask = np.squeeze(np.asanyarray(mask_image.dataobj)) > 0
assert mask.shape == (48, 48)
rows = []
for path in sorted(output.rglob('*.nii.gz')):
    image = nib.load(path)
    values = np.asanyarray(image.dataobj)
    row = {'path': str(path.relative_to(output)), 'shape': list(image.shape)}
    if tuple(values.shape[:2]) == mask.shape:
        assert np.allclose(image.affine, mask_image.affine)
        selected = values[mask]
        row.update(selected_values=int(selected.size), nonfinite_selected=int(np.count_nonzero(~np.isfinite(selected))))
        if not np.iscomplexobj(selected):
            finite = selected[np.isfinite(selected)]
            row.update(minimum=float(finite.min()), maximum=float(finite.max()), mean=float(finite.mean()))
    rows.append(row)
result = {'fsl_mrs_version': fsl_mrs.__version__, 'input_mask_shape': list(mask_image.shape), 'mask_voxels': int(mask.sum()), 'output_folders': sorted(p.name for p in output.iterdir() if p.is_dir()), 'nifti_files': rows, 'html_reports': [str(p.relative_to(output)) for p in sorted(output.rglob('*.html'))]}
report = Path.home() / 'neurodesktop-storage/tutorial-captures/fsl-mrsi-check.json'
report.write_text(json.dumps(result, indent=2) + '\n')
print('FSL-MRS:', result['fsl_mrs_version'])
print('Masked voxels:', result['mask_voxels'])
print('Saved NIfTI files:', len(rows))
print('Non-finite values inside mask:', sum(r.get('nonfinite_selected', 0) for r in rows))
print('Output folders:', ', '.join(result['output_folders']))
for row in rows:
    if 'NAA+NAAG' in row['path'] and row['path'].startswith('concs/'):
        print(row['path'], 'range:', row.get('minimum'), row.get('maximum'))
print('HTML reports:', len(result['html_reports']))

assert result['mask_voxels'] == 96
assert {'concs', 'fit', 'qc', 'uncertainties'}.issubset(result['output_folders'])
assert rows and all(r.get('selected_values', 0) >= 96 and r['nonfinite_selected'] == 0 for r in rows)
