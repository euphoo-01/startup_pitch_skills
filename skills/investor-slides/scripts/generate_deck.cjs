#!/usr/bin/env node
/**
 * INVESTOR SLIDES — editorial PPTX generator, brand-neutral by default.
 * Native PowerPoint typography, shapes and charts. Images remain images.
 *
 * node generate_deck.cjs examples/sample_deck.json --metrics demo/metrics.json \
 *   --monthly demo/monthly.json --market demo/market.json \
 *   --out demo/investor_pitch.pptx --manifest demo/deck_manifest.json
 *
 * This generator does NOT manufacture market, tax or financial facts.
 */
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const pptxgen = require('pptxgenjs');

const W=13.333333,H=7.5;
const THEMES={
  'editorial-blue':{paper:'F6F5F1',ink:'19212B',accent:'5267F5',accentInk:'FFFFFF',pale:'E8EBFF',line:'D9DAD8',muted:'646B78',white:'FFFFFF',dark:'18212C'},
  'graphite-lime':{paper:'F6F6F1',ink:'202420',accent:'C4EF70',accentInk:'17201B',pale:'EDF5DD',line:'D6DAD1',muted:'637067',white:'FFFFFF',dark:'1D2420'},
  'warm-coral':{paper:'F7F4EF',ink:'282422',accent:'D76D55',accentInk:'FFFFFF',pale:'F9E8E2',line:'DED6D0',muted:'736B67',white:'FFFFFF',dark:'2C2724'},
};
const TYPES = new Set(['cover','statement','split','steps','market','matrix','pricing','bullets','numbers','chart','economics','unit-economics','monthly-table','timeline','image','closing']);
function parseArgs(argv){
  const a={input:argv[2]};for(let i=3;i<argv.length;i+=2)a[argv[i].replace(/^--/,'')]=argv[i+1];
  if(!a.input||!a.out||!a.metrics)throw Error('Usage: generate_deck.cjs deck.json --metrics metrics.json --monthly monthly.json --market market.json --out deck.pptx [--manifest manifest.json]');
  return a;
}
function json(p){return JSON.parse(fs.readFileSync(p,'utf8'));}
function h(v,fallback){if(!v)return fallback;const x=String(v).replace(/^#/,'').toUpperCase();if(!/^[0-9A-F]{6}$/.test(x))throw Error('Invalid color '+v);return x;}
function get(o,key){let cur=o;for(const k of key.split('.')){if(cur===null||cur===undefined||!Object.prototype.hasOwnProperty.call(cur,k))throw Error(`Metric not found: ${key}`);cur=cur[k];}if(cur===null||cur===undefined)throw Error(`No metric value: ${key}`);return cur;}
function format(v,method='integer',unit=''){
  if(typeof v!=='number')return String(v);
  const loc=(x,d=0)=>new Intl.NumberFormat('ru-RU',{minimumFractionDigits:d,maximumFractionDigits:d}).format(x);
  let s;
  switch(method){
    case 'percent':s=loc(v*100,1)+'%';break;
    case 'multiple':s=loc(v,2)+'×';break;
    case 'fixed1':s=loc(v,1);break;
    case 'fixed2':s=loc(v,2);break;
    case 'compact':s=v>=1e9?loc(v/1e9,1)+' млрд':v>=1e6?loc(v/1e6,1)+' млн':v>=1e3?loc(v/1e3,1)+' тыс.':loc(v);break;
    case 'money_compact':s=v>=1e9?loc(v/1e9,1)+' млрд':v>=1e6?loc(v/1e6,1)+' млн':v>=1e3?loc(v/1e3,1)+' тыс.':loc(v);break;
    case 'integer':case 'currency':s=loc(v);break;
    default:throw Error('Unknown number format '+method);
  }
  return unit?s+' '+unit:s;
}
function run(){return Promise.resolve().then(async()=>{
  const args=parseArgs(process.argv),spec=json(args.input),raw=json(args.metrics),monthly=args.monthly?json(args.monthly):{};
  if(args.market)raw.market=json(args.market);
  if(!Array.isArray(spec.slides)||!spec.slides.length)throw Error('slides[] required');
  const th=spec.theme||{};const preset=THEMES[th.preset||'editorial-blue'];if(!preset)throw Error('Unknown preset; choose '+Object.keys(THEMES).join(','));
  const C={};for(const [k,v]of Object.entries(preset))C[k]=h(th[k],v);
  const FONT=th.font||'Inter', DISPLAY=th.headline_font||'Inter Display', MONO=th.mono_font||FONT;
  const pptx=new pptxgen();pptx.layout='LAYOUT_WIDE';pptx.lang=spec.language||'ru-RU';
  pptx.author=spec.author||'Investor Slides / synthetic deck';pptx.subject='Editable and metric-bound investor presentation';pptx.title=spec.title||'Investment case';
  pptx.theme={headFontFace:FONT,bodyFontFace:FONT,lang:pptx.lang};
  const S=pptx.ShapeType, manifest={checks:[],chart_checks:[],image_only_exceptions:[],theme:th.preset||'editorial-blue',slide_types:[]};
  const shape=(sl,x,y,w,h,fill,line='none',lw=0)=>sl.addShape(S.rect,{x,y,w,h,line:line==='none'?{color:fill,transparency:100}:{color:line,width:lw||1},fill:{color:fill}});
  const rule=(sl,x,y,w,color=C.line,width=1)=>sl.addShape(S.line,{x,y,w,h:0,line:{color,width}});
  function txt(sl,s,x,y,w,h,size=16,opt={}){
    let value=String(s||'');
    sl.addText(value,{x,y,w,h,fontFace:FONT,fontSize:size,color:C.ink,margin:0,vertAlign:'mid',breakLine:false,fit:'shrink',
      bold:false,...opt});
  }
  function small(sl,s,x,y,w,color=C.muted,size=9){txt(sl,String(s||'').toUpperCase(),x,y,w,.25,size,{bold:true,color,charSpacing:1.4});}
  function bound(sl,card,x,y,w,h,size=34,opt={}){
    let value;
    if(card.metric){const v=get(raw,card.metric);value=format(v,card.format||'integer',card.unit||'');manifest.checks.push({slide:sl.__number,metric_path:card.metric,raw_value:v,text:value});}
    else if(card.value!==undefined){value=String(card.value);if(/\d/.test(value)&&!card.source_id)throw Error('Numeric literal needs source_id: '+card.label);}
    else throw Error('Missing metric or literal value');
    txt(sl,value,x,y,w,h,size,{bold:true,...opt});return value;
  }
  function base(sl,i,item,{dark=false}={}){
    sl.__number=i+1;sl.background={color:dark?C.dark:C.paper};
    const fg=dark?C.white:C.ink,sub=dark?'A4AEBA':C.muted;
    rule(sl,.73,.54,11.87,dark?'414B59':C.line,0.7);
    small(sl,spec.brand||'INVESTMENT CASE',.75,.22,4.9,fg,9);
    small(sl,item.section||'INVESTMENT / BRIEF',8.55,.22,3.86,sub,8);
    small(sl,String(i+1).padStart(2,'0')+' / '+String(spec.slides.length).padStart(2,'0'),11.73,7.05,.78,sub,8);
    rule(sl,.73,6.92,11.87,dark?'414B59':C.line,0.7);
    manifest.slide_types.push({slide:i+1,type:item.type||'bullets'});
  }
  function heading(sl,item,{dark=false,y=1.05,size=38}={}){
    let t=item.title||item.headline||'';
    if(t.length>130)throw Error('Slide title too long '+t);
    txt(sl,t,.78,y,11.85,1.11,size,{bold:true,fontFace:DISPLAY,color:dark?C.white:C.ink,vertAlign:'top',breakLine:false});
  }
  function footer(sl,item,{dark=false}={}){if(item.note)txt(sl,item.note,.79,6.55,11.7,.24,9.5,{color:dark?'A4AEBA':C.muted});}
  function notes(sl,item){if(typeof sl.addNotes==='function'){if(item.speaker_note)sl.addNotes(String(item.speaker_note));if(item.sources)sl.addNotes('Sources/qualifications: '+item.sources.join('; '));}}
  function cell(sl,x,y,w,h,{dark=false}={}){shape(sl,x,y,w,h,dark?C.dark:C.white,dark?'414B59':C.line,.8);}
  function sectionNumber(sl,n,x,y){small(sl,String(n).padStart(2,'0'),x,y,.5,C.accent,10);}

  function monthlyRows(scenario){
    const rows=monthly[scenario];
    if(!Array.isArray(rows)||!rows.length)throw Error('Missing monthly scenario '+scenario);
    return rows;
  }
  function monthlyValue(row, field){
    switch(field){
      case 'month_number': return row.month_number;
      case 'month': return row.month;
      case 'payroll_with_tax': return (row.payroll||0)+(row.payroll_tax||0);
      case 'opex_cash': return (row.fixed_costs||0)+(row.payroll||0)+(row.payroll_tax||0)+(row.marketing||0);
      case 'funding_gap': return Math.max(0,-(row.ending_cash_committed||0));
      case 'funding_gap_to_reserve': return Math.max(0,-(row.ending_cash_committed||0));
      case 'investor_payout': return Math.max(0,row.investor_cash_flow||0);
      default:
        if(!(field in row)) throw Error('Unknown monthly field '+field);
        return row[field];
    }
  }
  function metricCard(sl, x, y, w, label, value, note, {dark=false}={}){
    shape(sl,x,y,w,.88,dark?C.dark:C.white,dark?'414B59':C.line,.8);
    small(sl,label,x+.14,y+.12,w-.26,dark?C.accent:C.muted,9.3);
    txt(sl,value,x+.14,y+.33,w-.28,.25,20,{bold:true,fontFace:DISPLAY,color:dark?C.white:C.ink});
    if(note) txt(sl,note,x+.14,y+.62,w-.26,.16,8.4,{color:dark?'AAB5C1':C.muted});
  }
  // Key unit economics belong in the main investor narrative, not just in Excel.
  // For a single subscription stream, insert the KPI spread automatically if omitted.
  // With multiple streams, require an explicit choice to avoid misleading blended LTV/CAC.
  const withUnitEconomics=Object.entries(raw.results||{}).some(([,v])=>v && Object.keys(v.subscription_ltv||{}).length);
  if(withUnitEconomics && !spec.slides.some(s=>s.type==='unit-economics') && spec.auto_unit_economics!==false){
    const scenario=spec.primary_scenario||'base', streams=Object.keys((raw.results[scenario]||{}).subscription_ltv||{});
    if(streams.length!==1)throw Error('Set a unit-economics slide with explicit stream; multiple subscription streams or no stream in primary scenario');
    const insertAfter=spec.slides.findIndex(s=>s.type==='numbers');
    const insertion=insertAfter>=0?insertAfter+1:Math.max(1,spec.slides.findIndex(s=>s.type==='chart'));
    spec.slides.splice(insertion,0,{type:'unit-economics',section:'UNIT ECONOMICS',title:'Юнит-экономика и маржа.',scenario,stream:streams[0],auto_generated:true});
  }
  const unitSlides=spec.slides.filter(s=>s.type==='unit-economics');
  if(unitSlides.length>1)throw Error('Only one unit-economics slide should be in the main deck');
  for(let i=0;i<spec.slides.length;i++){
    const it=spec.slides[i],type=it.type||'bullets';if(!TYPES.has(type))throw Error('Unknown slide type '+type);
    const sl=pptx.addSlide();const isDark=['cover','pricing','closing'].includes(type)||it.dark===true;
    base(sl,i,it,{dark:isDark});
    if(type==='cover'){
      // Punchy editorial cover: typography first, native geometry, no brand-specific imagery.
      shape(sl,10.05,.55,2.55,6.36,C.accent);
      shape(sl,10.05,.55,.12,6.36,C.dark);
      small(sl,it.eyebrow||'THE BUSINESS CASE',.83,1.12,7.8,C.accent,11);
      const title=it.headline||it.title||'';
      txt(sl,title,.80,1.77,9.0,2.78,53,{color:C.white,bold:true,fontFace:DISPLAY,vertAlign:'mid',breakLine:false});
      txt(sl,it.subtitle||'',.83,5.10,8.42,.88,18.5,{color:'C0C8D0',vertAlign:'top'});
      txt(sl,it.footer||'SYNTHETIC EXAMPLE · NOT INVESTMENT ADVICE',.84,6.57,8.0,.22,9,{color:'96A2AD'});
      txt(sl,it.year||'01',10.46,3.75,1.85,1.4,63,{bold:true,color:C.accentInk,align:'center'});
    }else if(type==='statement'){
      small(sl,it.eyebrow||'KEY INSIGHT',.82,1.08,9,C.accent,11);
      txt(sl,it.headline||it.title||'',.77,1.63,10.9,2.72,49,{bold:true,fontFace:DISPLAY,vertAlign:'mid'});
      rule(sl,.80,4.63,11.66,C.ink,1.1);
      txt(sl,it.subtitle||'',.83,5.0,9.52,1.13,20,{color:C.muted,vertAlign:'top'});
      if(it.side_label)small(sl,it.side_label,11.30,5.43,1.14,C.accent,10);
    }else if(type==='split'){
      heading(sl,it);
      cell(sl,.79,2.41,5.77,3.86,{dark:true});cell(sl,6.73,2.41,5.79,3.86);
      small(sl,it.left_title||'ТЕКУЩЕЕ СОСТОЯНИЕ',1.11,2.71,4.95,C.accent,11);
      txt(sl,it.left_body||'',1.10,3.30,4.98,2.48,23,{color:C.white,vertAlign:'top'});
      small(sl,it.right_title||'ПРЕДЛАГАЕМОЕ РЕШЕНИЕ',7.07,2.71,4.88,C.accent,11);
      txt(sl,it.right_body||'',7.07,3.30,4.95,2.48,23,{vertAlign:'top'});
      footer(sl,it);
    }else if(type==='steps'){
      heading(sl,it);const steps=it.steps||[];if(steps.length<2||steps.length>4)throw Error('Steps supports 2..4');
      const gx=.79, gap=.19,w=(11.73-(steps.length-1)*gap)/steps.length;
      steps.forEach((s,j)=>{
        const x=gx+j*(w+gap);rule(sl,x,2.49,w,C.ink,.9);
        txt(sl,String(j+1).padStart(2,'0'),x,2.74,w,1.03,55,{bold:true,color:j===0?C.accent:C.ink});
        txt(sl,s.title||'',x,4.02,w-.1,.68,19,{bold:true,vertAlign:'top'});
        txt(sl,s.body||'',x,4.95,w-.12,1.16,15,{color:C.muted,vertAlign:'top'});
      });footer(sl,it);
    }else if(type==='market'){
      heading(sl,it);const levels=it.levels||['PAM','TAM','SAM','SOM'];if(levels.length!==4)throw Error('market requires 4 levels');
      const gap=.13,sw=(11.74-gap*3)/4;
      levels.forEach((name,j)=>{
        const x=.78+j*(sw+gap),d=get(raw,'market.levels.'+name),highlight=j===3;
        cell(sl,x,2.36,sw,3.87,{dark:highlight});
        const ink=highlight?C.white:C.ink,muted=highlight?'A7B4C2':C.muted;
        small(sl,name,x+.22,2.60,sw-.42,highlight?C.accent:C.accent,11);
        txt(sl,format(d.audience,'compact'),x+.21,3.18,sw-.38,.75,31,{bold:true,color:ink});
        txt(sl,it.audience_label||'потенциальных клиентов',x+.22,3.98,sw-.45,.56,12.5,{color:muted});
        rule(sl,x+.22,4.83,sw-.45,highlight?'596474':C.line,.75);
        txt(sl,format(d.annual_revenue_potential,'money_compact'),x+.22,5.03,sw-.44,.64,25,{bold:true,color:ink});
        txt(sl,(raw.market.currency||'')+' / год',x+.22,5.69,sw-.38,.25,10.5,{color:muted});
        manifest.checks.push({slide:i+1,metric_path:'market.levels.'+name+'.audience',raw_value:d.audience,text:format(d.audience,'compact')});
        manifest.checks.push({slide:i+1,metric_path:'market.levels.'+name+'.annual_revenue_potential',raw_value:d.annual_revenue_potential,text:format(d.annual_revenue_potential,'money_compact')});
      });footer(sl,it);
    }else if(type==='matrix'){
      heading(sl,it);const headers=it.headers||[];const rows=it.rows||[];
      if(headers.length<2||headers.length>4||rows.length<2||rows.length>5)throw Error('matrix headers 2..4 and rows 2..5 required');
      const x=.79, y=2.36, colW=11.74/(headers.length+1), rowH=.65;
      shape(sl,x,y,11.74,.60,C.dark);
      txt(sl,it.row_header||'КРИТЕРИЙ',x+.16,y+.15,colW-.19,.30,9.5,{color:C.white,bold:true});
      headers.forEach((q,j)=>txt(sl,q,x+(j+1)*colW+.1,y+.10,colW-.19,.42,11,{color:j===headers.length-1?C.accent:C.white,bold:true}));
      rows.forEach((r,k)=>{
        const yy=y+.60+k*rowH;shape(sl,x,yy,11.74,rowH,k%2===0?C.white:C.paper);
        txt(sl,r.name,x+.17,yy+.10,colW-.27,rowH-.17,12.1,{bold:true});
        r.values.forEach((v,j)=>txt(sl,String(v),x+(j+1)*colW+.14,yy+.10,colW-.32,rowH-.18,12.2,{bold:j===headers.length-1,color:j===headers.length-1?C.accent:C.ink}));
        rule(sl,x,yy+rowH,11.74,C.line,.5);
      });footer(sl,it);
    }else if(type==='pricing'){
      heading(sl,it,{dark:true});shape(sl,.79,2.50,5.8,3.61,C.accent);
      small(sl,it.label||'ПОДПИСКА / ТАРИФ',1.11,2.83,5.1,C.accentInk,10);
      if(it.price_metric)bound(sl,{metric:it.price_metric,format:it.price_format||'currency',unit:it.currency||''},1.12,3.20,4.9,1.04,48,{color:C.accentInk});
      else txt(sl,it.price||'PRICE',1.12,3.17,4.9,1.17,48,{bold:true,color:C.accentInk});
      txt(sl,it.price_note||'за единицу в месяц',1.13,4.61,4.82,.42,15,{color:C.accentInk});
      (it.bullets||[]).slice(0,4).forEach((s,k)=>{
        txt(sl,String(k+1).padStart(2,'0'),7.01,2.71+k*.80,.42,.34,12,{bold:true,color:C.accent});
        txt(sl,s,7.60,2.68+k*.80,4.47,.60,16.5,{color:C.white});
      });footer(sl,it,{dark:true});
    }else if(type==='bullets'){
      heading(sl,it);const entries=it.bullets||[];if(entries.length>5)throw Error('bullets max 5');
      entries.forEach((b,j)=>{
        const y=2.25+j*.80;txt(sl,String(j+1).padStart(2,'0'),.83,y,.65,.51,22,{bold:true,color:C.accent});
        rule(sl,1.53,y+.57,10.96,C.line,.8);
        txt(sl,b,1.65,y,10.45,.54,20,{vertAlign:'mid'});
      });footer(sl,it);
    }else if(type==='numbers'){
      heading(sl,it);const cards=it.cards||[];if(cards.length<2||cards.length>4)throw Error('numbers supports 2..4');
      const g=.17,cw=(11.74-(cards.length-1)*g)/cards.length;
      cards.forEach((d,j)=>{
        const x=.78+j*(cw+g);if(j===cards.length-1){shape(sl,x,2.47,cw,3.49,C.dark);}else{shape(sl,x,2.47,cw,3.49,C.white);}
        const fg=j===cards.length-1?C.white:C.ink,sub=j===cards.length-1?'AAB5C1':C.muted;
        small(sl,d.label||'',x+.23,2.77,cw-.44,j===cards.length-1?C.accent:sub,10);
        bound(sl,{...d,unit:''},x+.20,3.49,cw-.41,.96,cards.length===4?29:37,{color:fg});
        if(d.unit)txt(sl,d.unit,x+.24,4.57,cw-.48,.33,13.5,{bold:true,color:sub});
        txt(sl,d.note||'',x+.24,5.11,cw-.48,.64,12,{color:sub,vertAlign:'top'});
      });footer(sl,it);
    }else if(type==='chart'){
      heading(sl,it);let series=[];
      for(const p of it.series||[]){const rows=monthlyRows(p.scenario);
        const vals=rows.map(r=>r[p.field]);if(vals.some(v=>typeof v!=='number'||!Number.isFinite(v)))throw Error('Invalid chart series '+p.field);
        const step=Math.max(1,Math.ceil(rows.length/8));
        series.push({name:p.label||p.scenario,labels:rows.map((r,j)=>(j%step===0||j===rows.length-1)?`M${r.month_number}`:''),values:vals.map(v=>v/(it.scale||1))});
      }
      if(!series.length)throw Error('chart must have series');
      manifest.chart_checks.push({chart_number:manifest.chart_checks.length+1,slide:i+1,scale:it.scale||1,series:(it.series||[]).map(p=>({scenario:p.scenario,field:p.field}))});
      cell(sl,.8,2.31,11.72,3.95);
      sl.addChart(it.chart_kind==='bar'?pptx.ChartType.bar:pptx.ChartType.line,series,{
        x:1.07,y:2.62,w:11.15,h:3.34,showLegend:series.length>1,legendPos:'b',legendFontSize:11,
        showTitle:false,showValue:false,showCatName:false,showSerName:false,showMarker:false,
        chartColors:[C.accent,C.ink,'91A0B2'],catAxisLabelFontFace:FONT,catAxisLabelFontSize:10,
        valAxisLabelFontFace:FONT,valAxisLabelFontSize:10,valAxisTitle:it.y_axis_label||'',
        showBorder:false,valGridLine:{color:'E8E9E7',width:.45},showLine:true,lineSize:2.6,
        showShadow:false,showDataLabelMarker:false,
      });
      if(it.y_axis_label) txt(sl,'Ось Y: '+it.y_axis_label,1.07,5.97,5.4,.22,9.3,{color:C.muted});
      footer(sl,it);
    }else if(type==='economics'){
      heading(sl,it);const items=it.cards||[];if(items.length!==3)throw Error('economics requires exactly 3 cards');
      items.forEach((d,j)=>{
        const y=2.29+j*1.28;rule(sl,.83,y,11.63,C.line,.8);
        txt(sl,String(d.label||'').toUpperCase(),.87,y+.17,4.65,.70,10.5,{color:C.muted,bold:true,charSpacing:1.0,vertAlign:'mid'});
        bound(sl,d,6.04,y+.18,6.16,.79,32,{align:'right'});
      });footer(sl,it);
    }else if(type==='unit-economics'){
      // Investor-first treatment: one dominant LTV/CAC number, with costs and margins
      // visible alongside. Never use revenue-LTV in a contribution-LTV ratio.
      heading(sl,it,{size:42});
      const scenario=it.scenario||spec.primary_scenario||'base';
      const r=get(raw,'results.'+scenario);
      const entries=Object.entries(r.subscription_ltv||{});
      const stream=it.stream||((entries.length===1)?entries[0][0]:null);
      if(!stream)throw Error('Unit economics needs a subscription stream ID when more than one or none exists');
      const u=r.subscription_ltv[stream];
      if(!u)throw Error('Subscription stream missing: '+stream);
      const cac=r.blended_marketing_cac_per_new_paid;
      const ltv=u.contribution_ltv_horizon,ratio=u.ltv_to_blended_cac;
      if(![cac,ltv,ratio,r.gross_margin,r.contribution_margin,u.paid_retention].every(v=>typeof v==='number'&&Number.isFinite(v)))
        throw Error('All Unit Economics KPI values must be finite, numeric, calculated before rendering');
      if(cac<=0||ltv<0)throw Error('CAC must be positive and LTV nonnegative');
      const moneyUnit=it.currency||r.currency||'';
      const addBound=(key,value,rendered)=>manifest.checks.push({slide:i+1,metric_path:key,raw_value:value,text:rendered});
      const root='results.'+scenario;
      const ratioTxt=format(ratio,'multiple'),cacTxt=format(cac,'fixed2',moneyUnit),ltvTxt=format(ltv,'fixed2',moneyUnit);
      const gTxt=format(r.gross_margin,'percent'),cTxt=format(r.contribution_margin,'percent'),retTxt=format(u.paid_retention,'percent');
      shape(sl,.79,2.31,5.47,3.15,C.dark);
      small(sl,'LTV / CAC',1.12,2.61,4.92,C.accent,12);
      txt(sl,ratioTxt,1.06,3.06,4.99,1.35,79,{bold:true,fontFace:DISPLAY,color:C.white});
      rule(sl,1.12,4.62,4.74,'586273',0.8);
      txt(sl,'Маржинальный LTV к стоимости привлечения',1.12,4.80,4.83,.38,12.5,{color:'C3CAD3'});
      small(sl,'CAC',6.68,2.56,2.45,C.muted,11);
      txt(sl,cacTxt,6.64,3.05,5.59,.68,36,{bold:true,fontFace:DISPLAY});
      rule(sl,6.69,3.87,5.62,C.line,0.8);
      small(sl,'LTV · contribution',6.68,4.07,3.65,C.muted,11);
      txt(sl,ltvTxt,6.64,4.51,5.59,.68,36,{bold:true,fontFace:DISPLAY});
      const labels=[['GROSS MARGIN',gTxt],['CONTRIBUTION MARGIN',cTxt],['MONTHLY RETENTION',retTxt]];
      labels.forEach(([label,value],j)=>{
        const x=.83+j*4.0;
        rule(sl,x,5.72,3.70,C.ink,0.8);
        small(sl,label,x,5.92,3.69,C.muted,9.0);
        txt(sl,value,x,6.18,3.65,.40,23,{bold:true,fontFace:DISPLAY});
      });
      addBound(root+'.subscription_ltv.'+stream+'.ltv_to_blended_cac',ratio,ratioTxt);
      addBound(root+'.blended_marketing_cac_per_new_paid',cac,cacTxt);
      addBound(root+'.subscription_ltv.'+stream+'.contribution_ltv_horizon',ltv,ltvTxt);
      addBound(root+'.gross_margin',r.gross_margin,gTxt);
      addBound(root+'.contribution_margin',r.contribution_margin,cTxt);
      addBound(root+'.subscription_ltv.'+stream+'.paid_retention',u.paid_retention,retTxt);
      if(typeof sl.addNotes==='function')sl.addNotes('Contribution LTV, not revenue LTV. CAC is blended marketing cost divided by newly paid customers. Retention is a scenario assumption unless validated by cohort data. All metrics come from '+root+' and subscription stream '+stream+'.');
      footer(sl,it);
    }else if(type==='monthly-table'){
      heading(sl,it,{size:40});
      const scenario=it.scenario||spec.primary_scenario||'base';
      const rows=monthlyRows(scenario);
      const start=Math.max(1,Number(it.start_month||1)), end=Math.min(rows.length,Number(it.end_month||rows.length));
      if(end < start) throw Error('monthly-table end_month must be >= start_month');
      const slice=rows.slice(start-1,end);
      if(slice.length>9) throw Error('monthly-table supports at most 9 months per slide; split into multiple slides');
      const res=get(raw,'results.'+scenario);
      const firstPayoutRow=rows.find(r => (r.investor_cash_flow||0) > 0);
      const firstPayout = firstPayoutRow ? 'M'+firstPayoutRow.month_number : 'не в горизонте';
      metricCard(sl,.80,1.78,2.65,'EBITDA > 0', 'M'+(res.first_ebitda_positive_month||'—'), 'первый плюсовой месяц');
      metricCard(sl,3.63,1.78,2.85,'MAX FUNDING NEED', format(res.additional_funding_required||0,'money_compact',it.currency||res.currency||''), 'макс. внешний капитал');
      metricCard(sl,6.67,1.78,2.40,'PAYOUT TO INVESTOR', firstPayout, 'начало возврата');
      metricCard(sl,9.27,1.78,3.25,'HORIZON CASH', format(res.cash_at_horizon||0,'money_compact',it.currency||res.currency||''), 'остаток на конце горизонта', {dark:true});
      const fields=(it.fields||[
        {field:'payroll_with_tax',label:'ФОТ+налоги',format:'money_compact'},
        {field:'marketing',label:'Маркетинг',format:'money_compact'},
        {field:'fixed_costs',label:'Постоянные',format:'money_compact'},
        {field:'capex',label:'CAPEX',format:'money_compact'},
        {field:'ebitda',label:'EBITDA',format:'money_compact'},
        {field:'funding_gap',label:'Пополнение',format:'money_compact'}
      ]);
      const x=.80,y=2.95,w=11.72; const cols=fields.length+1; const colW=w/cols; const rowH=.36;
      shape(sl,x,y,w,.42,C.dark);
      txt(sl,'МЕСЯЦ',x+.08,y+.08,colW-.16,.24,8.7,{color:C.white,bold:true});
      fields.forEach((f,j)=>txt(sl,String(f.label||f.field).toUpperCase(),x+(j+1)*colW+.08,y+.08,colW-.16,.24,8.1,{color:j===fields.length-1?C.accent:C.white,bold:true,align:'center'}));
      slice.forEach((row,idx)=>{
        const yy=y+.42+idx*rowH;
        shape(sl,x,yy,w,rowH,idx%2===0?C.white:C.paper);
        txt(sl,'M'+row.month_number,x+.07,yy+.07,colW-.12,.20,9.2,{bold:true});
        fields.forEach((f,j)=>{
          const rawValue=monthlyValue(row,f.field);
          const rendered=format(rawValue,f.format||'integer',f.unit||it.currency||res.currency||'');
          txt(sl,rendered,x+(j+1)*colW+.06,yy+.07,colW-.12,.20,8.5,{align:'center',color:(f.field==='ebitda'&&rawValue<0)?'AF3E3E':C.ink,bold:(f.field==='ebitda'||f.field==='funding_gap')});
          if(!['funding_gap','funding_gap_to_reserve','investor_payout','opex_cash','payroll_with_tax'].includes(f.field)){
            manifest.checks.push({slide:i+1,metric_path:`monthly.${scenario}.${start-1+idx}.${f.field}`,raw_value:rawValue,text:rendered});
          }
        });
      });
      txt(sl,it.caption||'Пополнение = ориентировочный объём внешнего капитала, необходимый в конце месяца, если проект нельзя оставлять с отрицательным cash.',.82,6.40,11.5,.34,8.8,{color:C.muted});
      footer(sl,it);
    }else if(type==='timeline'){
      heading(sl,it);const steps=it.steps||[];if(steps.length<2||steps.length>5)throw Error('timeline supports 2..5 steps');
      const x0=.83,y0=3.25,colW=11.72/steps.length;
      rule(sl,x0+.08,y0,colW*(steps.length-1),C.ink,1.4);
      steps.forEach((d,j)=>{
        const x=x0+j*colW;
        shape(sl,x,y0-.075,.15,.15,j===0?C.accent:C.ink);
        small(sl,d.when||'PHASE',x,2.62,colW-.20,C.accent,11);
        txt(sl,d.title||'',x,3.74,colW-.18,.78,17,{bold:true,vertAlign:'top'});
        txt(sl,d.body||'',x,4.77,colW-.18,1.17,12.3,{color:C.muted,vertAlign:'top'});
      });footer(sl,it);
    }else if(type==='image'){
      heading(sl,it);if(!it.image_path)throw Error('image_path required');
      const img=path.isAbsolute(it.image_path)?it.image_path:path.join(path.dirname(path.resolve(args.input)),it.image_path);
      if(!fs.existsSync(img))throw Error('Missing image: '+img);
      sl.addImage({path:img,x:.88,y:2.20,w:11.6,h:4.29,sizingContain:true});footer(sl,it);
    }else if(type==='closing'){
      shape(sl,10.13,.54,2.47,6.37,C.accent);
      small(sl,it.eyebrow||'INVESTMENT DECISION',.87,1.17,7.6,C.accent,10);
      txt(sl,it.headline||it.title||'',.82,1.80,8.74,2.69,51,{bold:true,fontFace:DISPLAY,color:C.white,vertAlign:'mid'});
      txt(sl,it.subtitle||'',.87,5.00,8.65,.96,18,{color:'B4BFC9',vertAlign:'top'});
      if(it.metric)bound(sl,{metric:it.metric,format:it.format||'money_compact',unit:it.unit||''},10.34,3.47,2.02,1.07,28,{color:C.accentInk,align:'center'});
      else txt(sl,it.side||'NEXT',10.44,3.55,1.85,.83,28,{bold:true,color:C.accentInk,align:'center'});
    }
    notes(sl,it);
  }
  await pptx.writeFile({fileName:args.out});
  if(args.manifest)fs.writeFileSync(args.manifest,JSON.stringify(manifest,null,2),'utf8');
  console.log(`Created ${spec.slides.length} slides [${th.preset||'editorial-blue'}] in ${args.out}`);
});}
run().catch(e=>{console.error(e.stack||e);process.exit(1)});
