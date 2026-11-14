import json
import math
import sys
import unittest
from copy import deepcopy
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'skills'/'business-analyst'/'scripts'))
from calculate import model, month_vector, irr_monthly
from validate import audit
from sizing import size_market


def example(filename='sample_saas.json'):
    return json.loads((ROOT/'examples'/filename).read_text(encoding='utf-8'))


class FinancialModelTests(unittest.TestCase):
    def setUp(self):
        self.data=example()

    def test_scenarios_and_conservation(self):
        result=model(self.data)
        self.assertEqual(set(result['results']), {'base','downside','upside'})
        self.assertEqual(result['project']['months'],18)
        for scenario in result['results'].values():
            monthly=scenario['monthly']
            self.assertEqual(len(monthly),18)
            self.assertLess(max(abs(r['balance_check']) for r in monthly),1e-5)
            self.assertAlmostEqual(sum(r['ebitda'] for r in monthly),scenario['metrics']['ebitda_total'])
            self.assertAlmostEqual(sum(r['revenue'] for r in monthly),scenario['metrics']['revenue_total'])
            self.assertGreaterEqual(scenario['metrics']['additional_funding_required'],0)
        self.assertGreater(result['results']['upside']['metrics']['revenue_total'],result['results']['base']['metrics']['revenue_total'])
        self.assertGreater(result['results']['base']['metrics']['revenue_total'],result['results']['downside']['metrics']['revenue_total'])

    def test_conversion_only_on_limit_month_or_after(self):
        rows=model(self.data)['results']['base']['monthly']
        self.assertTrue(all(row['streams']['plus']['converted_from_free']==0 for row in rows[:6]))
        self.assertGreater(rows[6]['streams']['plus']['converted_from_free'],0)

    def test_tax_payment_timing_and_vat(self):
        rows=model(self.data)['results']['base']['monthly']
        for idx,row in enumerate(rows):
            expected=rows[idx-1]['income_tax_accrued'] if idx>=1 else 0
            self.assertAlmostEqual(row['income_tax_paid'],expected)
            self.assertGreaterEqual(row['vat_paid'],-1e-9)

    def test_investor_returns_not_fabricated(self):
        m=model(self.data)['results']['base']['metrics']
        self.assertIsNone(m['investor_monthly_irr'])
        self.assertEqual(m['investor_moic'],0)
        self.assertIsNone(m['investor_cash_payback_month'])

    def test_coffee_negative_no_payback(self):
        m=model(example('sample_coffee.json'))['results']['base']['metrics']
        self.assertIsNone(m['project_fcf_payback_month'])
        self.assertIsInstance(m['break_even_primary_active_units'],int)
        self.assertLess(m['ebitda_total'],0)

    def test_break_even_no_positive_contribution(self):
        d=example('sample_coffee.json')
        d['revenues'][0]['unit_price']=0.1
        self.assertIsNone(model(d)['results']['base']['metrics']['break_even_primary_active_units'])

    def test_invalid_horizon_and_inputs(self):
        d=deepcopy(self.data)
        d['project']['months']=37
        with self.assertRaises(ValueError): model(d)
        d=deepcopy(self.data)
        d['revenues'][1]['id']='plus'
        with self.assertRaises(ValueError): model(d)

    def test_tax_readiness_blocker_and_strict(self):
        result=audit(self.data,strict=False)
        self.assertEqual(result['result'],'NOT_INVESTOR_READY')
        self.assertFalse(result['errors'])
        result=audit(self.data,strict=True)
        self.assertEqual(result['result'],'FAIL')
        self.assertTrue(result['errors'])

    def test_auditor_catches_stale_results(self):
        out=model(self.data)
        projection={'results':{k:v['metrics'] for k,v in out['results'].items()}}
        projection['results']['base']['ebitda_total']+=200
        checked=audit(self.data,projection)
        self.assertTrue(any('output stale' in x for x in checked['errors']))

    def test_irr_known_case(self):
        r=irr_monthly([-100,0,121])
        self.assertAlmostEqual(r,0.1,places=5)
        self.assertIsNone(irr_monthly([-100,150,-60,30]))

    def test_market_sizing_consistent(self):
        d=example('sample_market.json')
        m=size_market(d)
        ratio=m['levels']['SAM']['audience']/m['levels']['SOM']['audience']
        money=m['levels']['SAM']['annual_revenue_potential']/m['levels']['SOM']['annual_revenue_potential']
        self.assertAlmostEqual(ratio,money)
        d['market']['levels']['SAM']['basis']='annual_customers'
        with self.assertRaises(ValueError): size_market(d)


if __name__=='__main__':unittest.main()
