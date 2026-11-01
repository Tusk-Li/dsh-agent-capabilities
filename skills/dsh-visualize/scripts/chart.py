"""Build a self-contained interactive chart from labels and finite values."""
import argparse
import html
import json
import math
from pathlib import Path


def render(data):
    labels, values = data.get('labels'), data.get('values')
    if not isinstance(labels, list) or not isinstance(values, list) or not labels or len(labels) != len(values) or len(labels) > 500:
        raise ValueError('Provide 1 to 500 labels and matching values')
    if any(not isinstance(x, str) for x in labels) or any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in values):
        raise ValueError('Labels must be strings and values must be finite numbers')
    payload = json.dumps({'labels': labels, 'values': values}, ensure_ascii=False).replace('<', '\\u003c').replace('&', '\\u0026')
    title = html.escape(str(data.get('title', 'Chart')))
    return TEMPLATE.replace('TITLE_TEXT', title).replace('DATA_JSON', payload)


TEMPLATE = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TITLE_TEXT</title>
<style>body{font:16px system-ui;margin:0;background:#f3f6fb;color:#17243c}main{max-width:1000px;margin:40px auto;padding:28px;background:white;border-radius:18px}button,select{font:inherit;padding:8px;margin-right:12px}svg{width:100%;height:auto}table{border-collapse:collapse;width:100%}td,th{padding:9px;text-align:left;border-bottom:1px solid #dde3ee}#detail{min-height:1.5em}svg text{font:13px system-ui}</style>
<main><h1>TITLE_TEXT</h1><label>Chart <select id="mode"><option value="bar">Bar</option><option value="line">Line</option></select></label><button id="export">Export SVG</button><p id="detail" aria-live="polite">Hover a point or bar for details.</p><svg id="chart" viewBox="0 0 940 440" role="img" aria-label="TITLE_TEXT"></svg><details><summary>Data</summary><table><thead><tr><th>Label</th><th>Value</th></tr></thead><tbody id="rows"></tbody></table></details></main>
<script type="application/json" id="data">DATA_JSON</script><script>
const d=JSON.parse(document.getElementById('data').textContent),svg=document.getElementById('chart'),ns='http://www.w3.org/2000/svg';
function el(tag,a={},text){const e=document.createElementNS(ns,tag);for(const[k,v]of Object.entries(a))e.setAttribute(k,v);if(text!==undefined)e.textContent=text;svg.append(e);return e;}
function draw(){svg.replaceChildren();let lo=Math.min(0,...d.values),hi=Math.max(0,...d.values);if(lo===hi)hi=lo+1;const scale=Math.max(Math.abs(lo),Math.abs(hi),1),low=lo/scale,high=hi/scale,y=v=>360-(v/scale-low)/(high-low)*320,step=850/d.values.length,x=i=>65+step*(i+.5),zero=y(0);el('line',{x1:65,x2:915,y1:zero,y2:zero,stroke:'#8c99af'});for(let i=0;i<=4;i++){let v=low+(high-low)*i/4;el('text',{x:4,y:y(v*scale)+5},(v*scale).toLocaleString(undefined,{maximumSignificantDigits:4}));}if(document.getElementById('mode').value==='line')el('polyline',{points:d.values.map((v,i)=>`${x(i)},${y(v)}`).join(' '),fill:'none',stroke:'#245bce','stroke-width':3});d.values.forEach((v,i)=>{let e=document.getElementById('mode').value==='bar'?el('rect',{x:x(i)-step*.34,y:Math.min(zero,y(v)),width:step*.68,height:Math.max(1,Math.abs(y(v)-zero)),fill:'#245bce'}):el('circle',{cx:x(i),cy:y(v),r:5,fill:'#245bce'});const t=document.createElementNS(ns,'title');t.textContent=`${d.labels[i]}: ${v}`;e.append(t);e.onpointerenter=()=>document.getElementById('detail').textContent=`${d.labels[i]}: ${v}`;if(d.labels.length<=16)el('text',{x:x(i),y:390,'text-anchor':'middle'},d.labels[i]);});}
d.labels.forEach((label,i)=>{let tr=document.createElement('tr');for(const v of[label,d.values[i]]){let td=document.createElement('td');td.textContent=v;tr.append(td);}document.getElementById('rows').append(tr);});document.getElementById('mode').onchange=draw;document.getElementById('export').onclick=()=>{let clone=svg.cloneNode(true);clone.setAttribute('xmlns',ns);const u=URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(clone)],{type:'image/svg+xml'})),a=document.createElement('a');a.href=u;a.download='chart.svg';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);};draw();
</script></html>'''


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', required=True)
    p.add_argument('--output', required=True)
    args = p.parse_args()
    data = json.loads(Path(args.input).read_text(encoding='utf-8-sig'))
    result = render(data)
    path = Path(args.output).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as f:
        f.write(result)
    print(json.dumps({'file': str(path)}, ensure_ascii=False))
