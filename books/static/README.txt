Static assets for NeurodeskEDU

Folder layout
  branding/       NeurodeskEDU logos and variants
  supporters/     Funder and supporter logos
  guides/         Overview diagrams and startup guidance
  contribute/     Screenshots for contributor instructions
  examples/       Assets used by executable example notebooks
  tutorials/     Tutorial screenshots, grouped by topic and tutorial

Tutorial-specific screenshots belong in tutorials/<topic>/<tutorial>/, including
example downloads, selected input paths, processing steps and scientific results.
Reusable platform and application controls belong in neurodesk/media under
screenshots/neurodesk/. Link directly to that canonical file; do not keep a local
copy. A screenshot is shared because its content is reusable, not merely because
it shows a GUI. Generic launchers and empty tool windows can be reused; a selected
dataset, example-specific path or result belongs with the tutorial.

Use lowercase names with hyphens for new screenshot filenames. Keep topic
folders aligned with the existing books/tutorials/ sections. Put RISE images
in tutorials/about_neurodesk/rise-slideshow/ and tool-access images in
tutorials/about_neurodesk/accessing-neurodesk-tools/.

Capture screenshots from the actual application and inspect them before
referencing them. Do not replace an application result with an illustration.
Use descriptive alt text that explains the step or result.

Use the VNC desktop to preserve screen proportions. Close unrelated dialogs,
bring the relevant window fully into view and move the pointer away from
labels before capture. Check that menus and dialog controls are not clipped.
For click instructions, retain the original JPEG or PNG and add numbered SVG
overlays using docs/screenshot-annotations.json. Regenerate them with:
  python .github/scripts/annotate_tutorial_screenshots.py
The SVG embeds the unchanged capture; marker numbers must match the prose.
For the migrated raster guides, editable marker definitions live in
docs/tutorial-raster-guides.json. Keep unmarked working captures outside Git and run:
  python .github/scripts/render_tutorial_raster_guides.py --source-dir /path/to/captures

A file move must update both Markdown and notebook cell sources. Validate
all local image references from the repository root with:
  python .github/scripts/check_tutorial_assets.py books
  python .github/scripts/check_notebook_images.py books/tutorials books/examples
  (Limit this older checker to source folders after a local build; it also
  scans generated notebooks if passed all of books/.)

The migration map for retained assets is docs/tutorial-asset-moves.json.
Superseded screenshots removed after a refresh are listed in
docs/tutorial-retired-assets.json and remain recoverable from Git history. Existing screenshots
that have only moved retain their original pixels and are not evidence of
GUI testing on a new platform. The dated tutorial audit records which
screenshots have actually been recaptured and which GUI steps were tested.
