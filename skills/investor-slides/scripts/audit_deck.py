#!/usr/bin/env python3
"""Check PPTX textual metric bindings and presence of editable slide objects.

Usage: python audit_deck.py pitch.pptx --manifest manifest.json --metrics metrics.json --monthly monthly.json --market market.json
Requires stdlib only. This complements geometric/render-based QA, not replaces it.
"""
import argparse
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

NS = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main",
      "p": "http://schemas.openxmlformats.org/presentationml/2006/main"}


def metric(data, path):
    result = data
    for component in path.split("."):
        if isinstance(result, list) and component.isdigit():
            result = result[int(component)]
        else:
            result = result[component]
    return result


def normalized(s):
    return re.sub(r"\s+", " ", str(s)).strip().casefold()


def audit(deck, metrics, manifest, monthly=None, market=None):
    merged = dict(metrics)
    if market is not None:
        merged['market'] = market
    if monthly is not None:
        merged['monthly'] = monthly
    metrics = merged
    problems, warnings = [], []
    chart_xml = {}
    EMU=914400
    max_x, max_y = 13.33333 * EMU, 7.5 * EMU
    slides={}
    with zipfile.ZipFile(deck) as z:
        for item in z.namelist():
            if re.fullmatch(r"ppt/charts/chart\d+\.xml", item):
                chart_xml[int(re.search(r'chart(\d+)',item).group(1))] = ET.fromstring(z.read(item))
            if re.fullmatch(r"ppt/slides/slide\d+\.xml", item):
                number=int(re.search(r"slide(\d+)\.xml",item).group(1))
                root=ET.fromstring(z.read(item))
                text=" ".join((x.text or "") for x in root.findall(".//a:t", NS))
                textshapes=len(root.findall(".//p:sp",NS))
                pictures=len(root.findall(".//p:pic",NS))
                charts=len(root.findall(".//p:graphicFrame",NS))
                slides[number]={"text":text,"editable_shapes":textshapes,"pictures":pictures,"charts":charts}
                # Geometry bounds audit for native editable objects, not chart-internal shapes.
                for category in ('sp', 'pic', 'graphicFrame'):
                    for node in root.findall('.//p:'+category, NS):
                        xfrm = node.find('.//a:xfrm', NS)
                        if xfrm is None: continue
                        off,ext=xfrm.find('a:off',NS),xfrm.find('a:ext',NS)
                        if off is None or ext is None: continue
                        try:
                            x,y=int(off.get('x')),int(off.get('y'))
                            w,h=int(ext.get('cx')),int(ext.get('cy'))
                        except (TypeError, ValueError):continue
                        if min(x,y,w,h) < -100 or x+w>max_x+4000 or y+h>max_y+4000:
                            problems.append(f'Slide {number}: {category} object exceeds page bounds')
    exceptions=set(manifest.get("image_only_exceptions",[]))
    for i,item in sorted(slides.items()):
        if item["editable_shapes"]==0 and i not in exceptions:
            problems.append(f"Slide {i}: no native editable shapes; likely rasterized or blank")
        if item["pictures"]>=3 and item["editable_shapes"]<=1 and i not in exceptions:
            warnings.append(f"Slide {i}: many raster elements; inspect editability")
    if not slides:
        problems.append("No readable ppt/slides/slideN.xml found")
    for check in manifest.get("checks",[]):
        i=int(check["slide"])
        if i not in slides:
            problems.append(f"Manifest refers to missing slide {i}")
            continue
        mpath=check.get("metric_path") or check.get("metrics_path")
        if mpath:
            try: value=metric(metrics,mpath)
            except (KeyError,IndexError,TypeError) as exc:
                problems.append(f"Metric path missing {mpath}: {exc}")
                continue
            if "raw_value" in check and isinstance(value, (float, int)):
                if not math.isclose(float(check["raw_value"]), float(value), rel_tol=1e-9, abs_tol=1e-6):
                    problems.append(f"Slide {i}: stale bound metric {mpath}: {check['raw_value']} != {value}")
            expected=(check["text"] if "text" in check else check.get("format","{}").format(value))
        else:
            expected=check.get("text","")
        if normalized(expected) not in normalized(slides[i]["text"]):
            problems.append(f"Slide {i}: metric/text not found: {expected!r} (path={mpath or 'literal'})")
    if manifest.get('chart_checks') and monthly is None:
        warnings.append('Chart series not checked (pass --monthly monthly.json)')
    for spec in manifest.get('chart_checks', []) if monthly is not None else []:
        chart=chart_xml.get(int(spec['chart_number']))
        if chart is None:
            problems.append(f"Missing native chart {spec['chart_number']}")
            continue
        ns_c={'c':'http://schemas.openxmlformats.org/drawingml/2006/chart'}
        ser=chart.findall('.//c:ser',ns_c)
        if len(ser)!=len(spec['series']):
            problems.append(f"Chart {spec['chart_number']}: wrong number of series")
            continue
        for k,d in enumerate(spec['series']):
            try:
                expected=[float(x[d['field']])/float(spec.get('scale',1)) for x in monthly[d['scenario']]]
                actual=[float(pt.find('c:v',ns_c).text) for pt in ser[k].findall('.//c:val/c:numRef/c:numCache/c:pt',ns_c)]
            except (KeyError, ValueError, TypeError, ZeroDivisionError, AttributeError) as exc:
                problems.append(f"Chart {spec['chart_number']}: failed to parse data: {exc}")
                continue
            if len(expected)!=len(actual) or any(not math.isclose(a,b,rel_tol=1e-8,abs_tol=1e-7) for a,b in zip(expected,actual)):
                problems.append(f"Chart {spec['chart_number']}: series {k+1} diverges from monthly source")
    return {"slide_count":len(slides),"errors":problems,"warnings":warnings,
            "pass":not problems}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("pptx",type=Path)
    p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--metrics",type=Path,required=True)
    p.add_argument("--monthly",type=Path)
    p.add_argument("--market",type=Path)
    a=p.parse_args()
    report=audit(a.pptx,json.loads(a.metrics.read_text(encoding="utf-8")),
                 json.loads(a.manifest.read_text(encoding="utf-8")),
                 json.loads(a.monthly.read_text(encoding="utf-8")) if a.monthly else None,
                 json.loads(a.market.read_text(encoding="utf-8")) if a.market else None)
    print(json.dumps(report,indent=2,ensure_ascii=False))
    if report["errors"]:sys.exit(2)


if __name__=="__main__":main()
