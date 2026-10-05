import base64
import unittest

from offload_widget_volumes import offload


def encoded(data: bytes) -> str:
    return base64.b64encode(data).decode()


class OffloadTests(unittest.TestCase):
    def notebook(self, models):
        return {"metadata": {"widgets": {"application/vnd.jupyter.widget-state+json": {"state": models}}}}

    def test_embedded_files_and_afni_pairs_are_replaced_by_urls(self):
        volume = {"state": {"path": {"name": "anat+tlrc.HEAD"}, "url": None,
                            "paired_img_path": {"name": "anat+tlrc.BRIK"}, "paired_img_url": None},
                  "buffers": [{"path": ["paired_img_path", "data"], "encoding": "base64", "data": encoded(b"brik")},
                              {"path": ["path", "data"], "encoding": "base64", "data": encoded(b"head")}]}
        nifti = {"state": {"path": {"name": "T1w.nii.gz"}, "url": None},
                 "buffers": [{"path": ["path", "data"], "encoding": "base64", "data": encoded(b"nifti")}]}
        uploads = {}

        def upload(data, path_in_repo):
            uploads[path_in_repo] = data
            return "https://hf.test/" + path_in_repo

        notebook = self.notebook({"afni": volume, "nifti": nifti})
        self.assertEqual(offload(notebook, "data/examples/demo", upload), 3)
        self.assertEqual(sorted(uploads.values()), [b"brik", b"head", b"nifti"])
        names = {path.rsplit("/", 1)[1].rsplit("_", 1)[1]: path for path in uploads}
        self.assertEqual({name.split(".", 1)[1] for name in names}, {"HEAD", "BRIK", "nii.gz"})
        self.assertTrue(all(path.startswith("data/examples/demo/") for path in uploads))
        self.assertEqual(volume["state"]["url"], "https://hf.test/" + names[next(n for n in names if n.endswith(".HEAD"))])
        self.assertEqual(volume["state"]["paired_img_url"], "https://hf.test/" + names[next(n for n in names if n.endswith(".BRIK"))])
        self.assertEqual(volume["state"]["path"], {"data": None, "name": None})
        self.assertEqual(volume["buffers"], [])
        self.assertEqual(nifti["state"]["url"], "https://hf.test/" + names[next(n for n in names if n.endswith(".nii.gz"))])

    def test_other_widget_buffers_stay_embedded(self):
        buffers = [{"path": ["value"], "encoding": "base64", "data": encoded(b"x")},
                   {"path": ["draw_bitmap", "data"], "encoding": "base64", "data": encoded(b"y")}]
        model = {"state": {"value": None, "draw_bitmap": {}}, "buffers": list(buffers)}
        self.assertEqual(offload(self.notebook({"m": model}), "data/x", lambda *_: self.fail("uploaded")), 0)
        self.assertEqual(model["buffers"], buffers)


if __name__ == "__main__":
    unittest.main()
