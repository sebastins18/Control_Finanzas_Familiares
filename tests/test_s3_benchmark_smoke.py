"""Prueba de humo del benchmark S3: corre en pequeno y produce mediana, con y sin indices.

No fija tiempos absolutos (dependen del equipo). Comprueba la estructura del resultado,
que se exijan al menos 3 ejecuciones y que el plan cambie al quitar los indices.
"""
import os
import unittest
from unittest.mock import patch

from scripts import benchmark_s3


class S3BenchmarkSmokeTests(unittest.TestCase):
    def test_benchmark_reports_median_and_plan_change(self):
        with patch.dict(os.environ, {}, clear=False):
            loaded, results = benchmark_s3.run(count=400, runs=3)
        self.assertEqual(loaded, 400)
        self.assertEqual(len(results), 6)
        for item in results:
            self.assertEqual(len(item['timings']), 3)
            self.assertGreaterEqual(item['median'], min(item['timings']))
            self.assertLessEqual(item['median'], max(item['timings']))
        by_key = {(r['operation'], r['scenario']): ' '.join(r['plan']) for r in results}
        date_op = benchmark_s3.operations(400)[0][0]
        self.assertIn('USING INDEX', by_key[(date_op, 'con indices')])
        self.assertIn('SCAN', by_key[(date_op, 'sin indices')])

    def test_fewer_than_three_runs_are_rejected(self):
        with self.assertRaises(ValueError):
            benchmark_s3.run(count=100, runs=2)


if __name__ == '__main__':
    unittest.main()