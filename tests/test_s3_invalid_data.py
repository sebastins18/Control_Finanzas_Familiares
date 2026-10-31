"""Datos invalidos (Seguimiento 3): la aplicacion rechaza entradas incorrectas sin escribir.

Cada caso debe responder con error controlado (400/409/403, nunca 500) y dejar el
numero de movimientos intacto.
"""
import unittest
from urllib.error import HTTPError

from tests.test_s3_normal import S3HttpBase


class S3InvalidDataTests(S3HttpBase):
    def rejected(self, overrides):
        before = self.count_movements()
        form = dict(self.form(), **overrides)
        with self.assertRaises(HTTPError) as caught:
            self.post(form, '/movimientos')
        code = caught.exception.code
        caught.exception.close()
        self.assertIn(code, (400, 409), overrides)
        self.assertEqual(self.count_movements(), before, overrides)

    def test_negative_or_zero_amount_is_rejected(self):
        self.rejected({'monto': '-5'})
        self.rejected({'monto': '0'})

    def test_non_numeric_and_too_many_decimals_are_rejected(self):
        self.rejected({'monto': 'abc'})
        self.rejected({'monto': '10.999'})

    def test_invalid_date_is_rejected(self):
        self.rejected({'fecha': '2026-13-45'})
        self.rejected({'fecha': '15/10/2026'})

    def test_unknown_type_category_or_account_is_rejected(self):
        self.rejected({'tipo': 'regalo'})
        self.rejected({'id_categoria': '999999'})
        self.rejected({'id_cuenta': '999999'})
        self.rejected({'id_cuenta': 'no-es-numero'})


if __name__ == '__main__':
    unittest.main()