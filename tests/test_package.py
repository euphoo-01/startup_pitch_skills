import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'skills'/'investor-slides'/'scripts'))
from audit_deck import audit


class PackageTests(unittest.TestCase):
    def test_install_codex_cursor_claude_without_duplicate(self):
        with tempfile.TemporaryDirectory() as temp:
            p=subprocess.run([sys.executable,str(ROOT/'install.py'),'--target','all','--project',temp],capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr)
            expected=Path(temp)
            for path in ('.agents/skills/business-analyst/SKILL.md',
                         '.agents/skills/investor-slides/SKILL.md',
                         '.claude/skills/business-analyst/SKILL.md',
                         '.claude/skills/investor-slides/SKILL.md'):
                self.assertTrue((expected/path).is_file())
            self.assertFalse((expected/'.cursor/skills').exists())  # Cursor reads .agents

    def test_frontmatter(self):
        for sk in (ROOT/'skills').iterdir():
            text=(sk/'SKILL.md').read_text(encoding='utf-8')
            self.assertTrue(text.startswith('---\nname: '+sk.name+'\n'))
            self.assertIn('\ndescription: ',text)
            self.assertLess(len(text.split()),750)

    @unittest.skipUnless(shutil.which('node'), 'Node.js missing')
    def test_native_editable_generator(self):
        probe=subprocess.run(['node','-e',"require('pptxgenjs')"],capture_output=True,text=True)
        if probe.returncode:
            self.skipTest('PptxGenJS not installed')
        import importlib.util
        sys.path.insert(0,str(ROOT/'skills'/'business-analyst'/'scripts'))
        from calculate import model
        example=json.loads((ROOT/'examples'/'sample_b2b.json').read_text(encoding='utf-8'))
        calculated=model(example)
        with tempfile.TemporaryDirectory() as temp:
            t=Path(temp)
            metrics=t/'metrics.json'; monthly=t/'monthly.json'; outfile=t/'pitch.pptx'; manifest=t/'manifest.json'; market=t/'market.json'
            metrics.write_text(json.dumps({'results':{k:v['metrics'] for k,v in calculated['results'].items()}}))
            monthly.write_text(json.dumps({k:v['monthly'] for k,v in calculated['results'].items()}))
            from sizing import size_market
            market.write_text(json.dumps(size_market(example)))
            script=ROOT/'skills'/'investor-slides'/'scripts'/'generate_deck.cjs'
            proc=subprocess.run(['node',str(script),str(ROOT/'examples'/'sample_deck.json'),'--metrics',str(metrics),
                                 '--monthly',str(monthly),'--market',str(market),'--out',str(outfile),'--manifest',str(manifest)],capture_output=True,text=True)
            self.assertEqual(proc.returncode,0,proc.stderr)
            self.assertTrue(outfile.exists())
            contents=ZipFile(outfile).namelist()
            self.assertEqual(sum(x.startswith('ppt/slides/slide') and x.endswith('.xml') for x in contents),15)
            self.assertTrue(any(x.startswith('ppt/charts/chart') and x.endswith('.xml') for x in contents))
            full_audit=audit(outfile,json.loads(metrics.read_text()),json.loads(manifest.read_text()),json.loads(monthly.read_text()),json.loads(market.read_text()))
            self.assertTrue(full_audit['pass'],full_audit)
            text_manifest=json.loads(manifest.read_text())
            for field in ('ltv_to_blended_cac','contribution_ltv_horizon','blended_marketing_cac_per_new_paid','gross_margin','contribution_margin','paid_retention'):
                self.assertTrue(any(field in x.get('metric_path','') for x in text_manifest['checks']),field)
            import copy
            stale=json.loads(metrics.read_text())
            stale['results']['base']['subscription_ltv']['workspace']['ltv_to_blended_cac']+=1
            self.assertFalse(audit(outfile,stale,text_manifest,json.loads(monthly.read_text()),json.loads(market.read_text()))['pass'])

    def test_theme_is_not_tied_to_sample_startup(self):
        generator=(ROOT/'skills'/'investor-slides'/'scripts'/'generate_deck.cjs').read_text(encoding='utf-8').lower()
        self.assertNotIn('зачёт',generator)
        self.assertNotIn('zachet',generator)
        self.assertIn('editorial-blue',generator)
        self.assertIn('warm-coral',generator)

    def test_pptx_text_audit(self):
        xml='''<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><p:cSld><p:spTree><p:sp><p:txBody><a:p><a:r><a:t>Project EBITDA 4567</a:t></a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld></p:sld>'''
        with tempfile.TemporaryDirectory() as temp:
            filename=Path(temp)/'test.pptx'
            with ZipFile(filename,'w') as z:
                z.writestr('ppt/slides/slide1.xml',xml)
            met={'results':{'base':{'ebitda_total':4567}}}
            good={'checks':[{'slide':1,'metrics_path':'results.base.ebitda_total','format':'{:.0f}'}]}
            bad={'checks':[{'slide':1,'text':'98765'}]}
            self.assertTrue(audit(filename,met,good)['pass'])
            self.assertFalse(audit(filename,met,bad)['pass'])

if __name__=='__main__':unittest.main()
