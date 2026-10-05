import unittest

from review_ci_gate import LOOKBACK_RUNS, evaluate


def run(n, sha="new"):
    return {"id": n, "head_sha": sha, "html_url": f"run/{n}"}


def job(conclusion):
    return {"conclusion": conclusion, "html_url": "job"}


class GateTests(unittest.TestCase):
    def evaluate(self, candidates, results):
        """results: list of (run, {path: job}) newest first."""
        jobs = {r["id"]: j for r, j in results}
        return evaluate(candidates, (r for r, _ in results), lambda r: jobs[r["id"]],
                        lambda sha, path: "same-blob")

    def test_cancelled_job_waits_quietly(self):
        gated, held = self.evaluate([{"source_path": "a.ipynb"}],
                                    [(run(1), {"a.ipynb": job("cancelled")})])
        self.assertEqual(gated, [])
        self.assertFalse(held[0]["notify"])

    def test_failed_job_notifies(self):
        _, held = self.evaluate([{"source_path": "a.ipynb"}], [(run(1), {"a.ipynb": job("failure")})])
        self.assertTrue(held[0]["notify"])

    def test_existing_closed_issue_skips_the_gate(self):
        candidate = {"source_path": "a.ipynb", "issue_exists": True, "issue_open": False}
        gated, held = self.evaluate([candidate], [])
        self.assertEqual((gated, held), ([candidate], []))

    def test_result_older_than_the_first_page_is_found(self):
        results = [(run(n), {}) for n in range(150)] + [(run(150), {"a.ipynb": job("success")})]
        gated, _ = self.evaluate([{"source_path": "a.ipynb"}], results)
        self.assertEqual([c["source_path"] for c in gated], ["a.ipynb"])
        self.assertGreater(LOOKBACK_RUNS, 150)

    def test_runs_stop_being_read_once_every_notebook_has_a_result(self):
        read = []
        def runs():
            for n in range(10):
                read.append(n)
                yield run(n)
        evaluate([{"source_path": "a.ipynb"}], runs(), lambda r: {"a.ipynb": job("success")},
                 lambda sha, path: "same-blob")
        self.assertEqual(read, [0, 1])


if __name__ == "__main__":
    unittest.main()
