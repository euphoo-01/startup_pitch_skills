import importlib.util
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'skills'/'business-analyst'/'scripts'))
from calculate import model


@unittest.skipUnless(importlib.util.find_spec('artifact_tool'), 'artifact_tool not available')
class ExcelParityTests(unittest.TestCase):
    def test_spreadsheet_formulas_match_python(self):
        from artifact_tool import Blob,SpreadsheetFile
        from export_excel import export
        data=json.loads((ROOT/'examples'/'sample_saas.json').read_text(encoding='utf-8'))
        predicted=model(data)
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'financial_model.xlsx'
            export(data,path)
            self.assertTrue(path.exists())
            wb=SpreadsheetFile.import_xlsx(Blob.load(str(path)))
            answer=json.loads(wb.inspect({'kind':'table','range':'Summary!A4:J6',
                       'include':'values','table_max_rows':3,'table_max_cols':10}).ndjson)
            for row in answer['values']:
                name=row[0]
                metrics=predicted['results'][name]['metrics']
                self.assertTrue(math.isclose(row[1],metrics['revenue_total'],abs_tol=0.0001))
                self.assertTrue(math.isclose(row[2],metrics['ebitda_total'],abs_tol=0.0001))
                self.assertTrue(math.isclose(row[3],metrics['additional_funding_required'],abs_tol=0.0001))
                self.assertTrue(math.isclose(row[4],metrics['project_fcf_at_horizon'],abs_tol=0.0001))
                self.assertEqual(row[5],metrics['break_even_primary_active_units'])
                self.assertEqual(row[6],metrics['project_fcf_payback_month'])
                self.assertTrue(math.isclose(row[7],metrics['blended_marketing_cac_per_new_paid'],abs_tol=0.0001))
                self.assertLess(abs(row[9]),1e-6)


if __name__=='__main__':unittest.main()
