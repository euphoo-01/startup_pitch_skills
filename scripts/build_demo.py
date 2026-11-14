#!/usr/bin/env python3
"""Rebuild a synthetic B2B example: deterministic model -> market -> PPTX (+ optional Excel, PDF).

Does not fetch external data or invent validated claims. All demo assumptions are fictional.
"""
from __future__ import annotations
import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'skills' / 'business-analyst' / 'scripts'
S = ROOT / 'skills' / 'investor-slides' / 'scripts'
DEMO = ROOT / 'demo'


def call(args):
    print('+', ' '.join(str(s) for s in args))
    subprocess.run([str(a) for a in args], check=True, cwd=ROOT)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--no-excel', action='store_true', help='skip artifact_tool workbook export')
    p.add_argument('--no-pdf', action='store_true', help='skip LibreOffice PDF conversion')
    args=p.parse_args()
    DEMO.mkdir(parents=True,exist_ok=True)
    sample=ROOT/'examples'/'sample_b2b.json'
    call([sys.executable, P/'calculate.py', sample, '--out', DEMO])
    call([sys.executable, P/'sizing.py', sample, '--out', DEMO/'market.json'])
    call(['node', S/'generate_deck.cjs', ROOT/'examples'/'sample_deck.json',
          '--metrics', DEMO/'metrics.json', '--monthly', DEMO/'monthly.json',
          '--market', DEMO/'market.json', '--out', DEMO/'investor_pitch.pptx',
          '--manifest', DEMO/'deck_manifest.json'])
    call([sys.executable,S/'audit_deck.py',DEMO/'investor_pitch.pptx',
          '--metrics',DEMO/'metrics.json','--manifest',DEMO/'deck_manifest.json',
          '--monthly',DEMO/'monthly.json', '--market', DEMO/'market.json'])
    if not args.no_excel:
        try:
            import artifact_tool  # noqa: F401
        except ImportError:
            print('artifact_tool unavailable — Excel export skipped.')
        else:
            call([sys.executable,P/'export_excel.py',sample,'--out',DEMO/'financial_model.xlsx'])
    if not args.no_pdf:
        soffice=shutil.which('libreoffice') or shutil.which('soffice')
        if soffice:
            with tempfile.TemporaryDirectory() as temp:
                call([soffice,'-env:UserInstallation=file://'+temp+'/profile',
                      '--headless','--convert-to','pdf','--outdir',DEMO,DEMO/'investor_pitch.pptx'])
        else:print('LibreOffice unavailable — PDF export skipped.')
    print('Demo output:', DEMO)

if __name__ == '__main__':main()
