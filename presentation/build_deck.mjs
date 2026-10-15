import fs from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const BUILD = path.join(ROOT, '.presentation-build');
const OUT = path.join(ROOT, 'presentation');
const FINAL = path.join(OUT, 'Global_Happiness_Insights_2025.pptx');
const RUN_ID = Date.now().toString();
const STAGE_DIR = path.join(OUT, '.staging');
const STAGED_FINAL = path.join(STAGE_DIR, `Global_Happiness_Insights_2025_validated_${RUN_ID}.pptx`);
const W = 1280, H = 720;
const C = { navy:'#16324A', teal:'#147D78', coral:'#D86E50', cream:'#F7F5EF', white:'#FFFFFF', ink:'#20384B', muted:'#607486', line:'#DCE4E8', pale:'#E9F2F0', soft:'#F0F3F5' };
const FONT = 'Arial';
const TOOLKIT = process.env.PRESENTATION_TOOLKIT_DIR;
const runtimeModules = process.env.RUNTIME_NODE_MODULES || process.env.NODE_PATH;
if (!TOOLKIT || !runtimeModules) {
  throw new Error('Set PRESENTATION_TOOLKIT_DIR and RUNTIME_NODE_MODULES (or NODE_PATH) to rebuild and validate this deck.');
}
process.env.RUNTIME_NODE_MODULES = runtimeModules;
const require = createRequire(import.meta.url);
const { Presentation, PresentationFile } = require('@oai/artifact-tool');

function csv(text) {
  const lines = text.trim().split(/\r?\n/);
  const rows = lines.map(line => {
    const cells=[]; let value='', quote=false;
    for (let i=0;i<line.length;i++) {
      const ch=line[i];
      if (ch==='"' && line[i+1]==='"' && quote) { value+='"'; i++; }
      else if (ch==='"') quote=!quote;
      else if (ch===',' && !quote) { cells.push(value); value=''; }
      else value+=ch;
    }
    cells.push(value); return cells;
  });
  return rows.slice(1).map(row => Object.fromEntries(rows[0].map((h,j)=>[h,row[j]])));
}
const getRows = async f => csv(await fs.readFile(path.join(ROOT,'outputs',f),'utf8'));
const n = value => Number(value);
const pValue = value => {
  const p = Number(value);
  if (!Number.isFinite(p)) return 'not available';
  if (p < 0 || p > 1) return 'invalid';
  if (p === 0) return '0 (underflow)';
  return p < 0.0001 ? p.toExponential(3) : p.toPrecision(4).replace(/(\.\d*?[1-9])0+$/, '$1').replace(/\.0+$/, '');
};
const top = await getRows('top_10_countries.csv');
const bottom = await getRows('bottom_10_countries.csv');
const correlations = await getRows('correlation_analysis.csv');
const groups = await getRows('group_comparison.csv');
const cleaned = await getRows('cleaned_happiness.csv');
const q = JSON.parse(await fs.readFile(path.join(ROOT,'outputs','data_quality_report.json'),'utf8'));
const names = { 'GDP per capita':'Explained by: Log GDP per capita', 'Social support':'Explained by: Social support',
  'Healthy life expectancy':'Explained by: Healthy life expectancy', 'Freedom to make life choices':'Explained by: Freedom to make life choices',
  'Generosity':'Explained by: Generosity', 'Perceptions of corruption':'Explained by: Perceptions of corruption' };
const highest = top[0], lowest=bottom[bottom.length-1];
const india=cleaned.find(x=>x['Country name']==='India');
const finland=cleaned.find(x=>x['Country name']==='Finland');
const validCorrelations=correlations.filter(r=>r.status==='ok'&&Number.isFinite(n(r.pearson_r)));
const positiveCorrelations=validCorrelations.filter(r=>n(r.pearson_r)>0);
const negativeCorrelations=validCorrelations.filter(r=>n(r.pearson_r)<0);
const pearsonBest=positiveCorrelations.sort((a,b)=>n(b.pearson_r)-n(a.pearson_r))[0];
const pearsonNegative=negativeCorrelations.sort((a,b)=>n(a.pearson_r)-n(b.pearson_r))[0];
const weak=[...validCorrelations].sort((a,b)=>Math.abs(n(a.pearson_r))-Math.abs(n(b.pearson_r)))[0];
const positiveText=pearsonBest?`Strongest positive Pearson association: ${pearsonBest.factor}, r=${n(pearsonBest.pearson_r).toFixed(3)}.`:'No positive Pearson coefficients were observed among valid results.';
const negativeText=pearsonNegative?`Strongest negative Pearson association: ${pearsonNegative.factor}, r=${n(pearsonNegative.pearson_r).toFixed(3)}.`:'No negative Pearson coefficients were observed among valid results.';
const weakText=weak?`Weakest absolute Pearson association: ${weak.factor}, r=${n(weak.pearson_r).toFixed(3)}.`:'Pearson association summaries are unavailable because no valid coefficients were calculated.';
const gap=n(highest['Ladder score'])-n(lowest['Ladder score']);

await fs.mkdir(BUILD,{recursive:true}); await fs.mkdir(OUT,{recursive:true}); await fs.mkdir(STAGE_DIR,{recursive:true});
const presentation = Presentation.create({slideSize:{width:W,height:H}});

function text(slide, value, x,y,w,h, size=24, color=C.ink, bold=false, opts={}) {
  let s;
  try {
    s=slide.shapes.add({geometry:'textbox',name:opts.name,position:{left:x,top:y,width:w,height:h},fill:'none',line:{style:'solid',fill:'none',width:0}});
    s.text=String(value);
    s.text.style={fontSize:size,color,bold,typeface:FONT,verticalAlignment:opts.valign||'top',alignment:opts.align||'left',wrap:'square',autoFit:'shrinkText',insets:0};
  } catch (e) { console.error('TEXT COLOR ISSUE',JSON.stringify({value:String(value).slice(0,40),color,size}),e); throw e; }
  return s;
}
function rect(slide,x,y,w,h,fill,line='none',radius='rect') {
  try { return slide.shapes.add({geometry:radius,position:{left:x,top:y,width:w,height:h},fill,line:{style:'solid',fill:line,width:line==='none'?0:1}}); }
  catch(e) { console.error('RECT COLOR ISSUE',JSON.stringify({fill,line,radius}),e); throw e; }
}
function base(title,kicker='GLOBAL HAPPINESS INSIGHTS 2025') {
  const s=presentation.slides.add(); s.background.fill=C.cream;
  text(s,kicker,64,32,950,24,14,C.teal,true);
  text(s,title,64,66,1152,60,42,C.navy,true);
  rect(s,64,138,70,4,C.teal);
  text(s,String(presentation.slides.items.length).padStart(2,'0'),1170,666,45,22,15,C.muted,true,{align:'right'});
  return s;
}
function notes(slide, extra='') {
  slide.speakerNotes.text=[
    'Dataset: user-supplied WHR_2025.xls, sheet Sheet1. Analysis results were calculated by this reconstructed project and are not claimed to reproduce the original internship analysis.',
    'World Happiness Report 2025, Country Rankings and Figure 2.1 (Gallup World Poll, 2022–2024): https://files.worldhappiness.report/WHR25.pdf',
    extra,
  ].filter(Boolean).join('\n\n');
}
function bulletLines(slide, lines, x,y,w, size=22, color=C.ink, lineGap=54) {
  lines.forEach((line,i)=>{ rect(slide,x,y+i*lineGap+8,9,9,C.teal,'none','ellipse'); text(slide,line,x+25,y+i*lineGap,w-25,lineGap-4,size,color,false); });
}
function addNativeBar(slide,{title,categories,series,position,direction='bar',hasLegend=false,format='0.000',min,max}) {
  const valueAxis={...(min!==undefined?{min}:{}),...(max!==undefined?{max}:{}),...(format?{numberFormatCode:format}:{}),
    textStyle:{fontSize:13,fill:C.muted},majorGridlines:{style:'solid',fill:C.line,width:1}};
  const categoryAxis={textStyle:{fontSize:14,fill:C.ink},majorGridlines:null};
  return slide.charts.add('bar',{position,title,titleTextStyle:{fontSize:19,fill:C.navy,bold:true},categories,
    series,hasLegend,legend:{position:'bottom',overlay:false,textStyle:{fontSize:14,fill:C.muted}},
    barOptions:{direction,grouping:series.length>1?'clustered':'clustered',gapWidth:60,overlap:0},
    xAxis:direction==='bar'?valueAxis:categoryAxis,
    yAxis:direction==='bar'?categoryAxis:valueAxis,
    dataLabels:{showValue:true,position:'outEnd',...(format?{numberFormatCode:format}:{}),textStyle:{fontSize:12,fill:C.ink}}});
}

// 1 — Cover
{
 const s=presentation.slides.add(); s.background.fill=C.navy;
 rect(s,0,0,16,H,C.teal);
 text(s,'GLOBAL HAPPINESS\nINSIGHTS 2025',82,124,770,190,58,C.white,true);
 text(s,'Country rankings, explanatory components, and an interactive exploration',86,348,680,78,25,'#D7E4E9',false);
 rect(s,86,476,95,5,C.coral);
 text(s,'A reproducible data analysis using the supplied World Happiness Report workbook',86,505,760,56,20,'#D7E4E9');
 text(s,'147 countries  /  Report period 2022–2024',86,623,620,28,17,'#B9CBD3',true);
  text(s,'Repository: [add URL after publication]  ·  Author: [add name]',86,666,1020,22,14,'#B9CBD3');
 notes(s);
}
// 2 — Problem and objectives
{
 const s=base('Questions this project answers');
 text(s,'A clear country ranking is a starting point. The analysis also compares six report components and quantifies how they associate with Ladder score.',64,174,1070,76,25,C.ink);
 bulletLines(s,[
  'Which countries sit at the top and bottom of the 2025 ranking?',
  'How do Finland and India compare in rank and score?',
  'Which available factors show the strongest country-level association with Ladder score?',
  'How do the top 10 and bottom 10 differ on the report components?',
 ],86,290,1040,22,C.ink,66);
 text(s,'Scope: descriptive analysis of 147 country aggregates. No causal effects or year-to-year trends are estimated.',86,596,1050,45,18,C.muted,true);
 notes(s);
}
// 3 — Dataset
{
 const s=base('Dataset and source');
 text(s,'WHR_2025.xls  ·  Sheet1  ·  147 rows  ·  11 columns',64,172,1100,42,25,C.teal,true);
 text(s,'The workbook contains one country-level record per country. Ladder score is the ranking measure. The six “Explained by” fields are report components used here as explanatory indicators.',64,228,1080,96,23,C.ink);
 rect(s,64,358,530,222,C.white,C.line);
 text(s,'KEY FIELDS',88,380,440,27,15,C.teal,true);
 bulletLines(s,['Country name and Ladder score','GDP per capita and social support','Healthy life expectancy and freedom','Generosity and perceptions of corruption'],88,423,470,19,C.ink,36);
 rect(s,630,358,586,222,C.pale,'none');
 text(s,'COVERAGE AND LIMITS',654,380,500,27,15,C.teal,true);
 text(s,'The workbook has no year, region, or income-level columns. Its ranking structure and values align with the report’s 2022–2024 country ranking.',654,424,520,104,21,C.ink);
 text(s,'Source: World Happiness Report 2025, Figure 2.1, Gallup World Poll 2022–2024. Citation in speaker notes.',654,535,520,38,14,C.muted);
 notes(s,'The official source documents the ranking period and report context. The file itself has no year column.');
}
// 4 — Cleaning
{
 const s=base('Data cleaning and validation');
 const missing=Object.entries(q.missing_after_cleaning).filter(([,v])=>v>0).map(([k,v])=>`${k}: ${v}`);
 text(s,'147 → 147',64,176,300,66,45,C.teal,true);
 text(s,'Rows retained',66,239,250,28,18,C.muted,true);
 text(s,'0',406,176,160,66,45,C.teal,true);
 text(s,'Duplicate countries',408,239,260,28,18,C.muted,true);
 text(s,'No imputation',744,176,350,66,38,C.coral,true);
 text(s,'Missing values kept as missing',746,239,420,28,18,C.muted,true);
 rect(s,64,322,530,242,C.white,C.line);
 text(s,'VALIDATION CHECKS',88,344,440,24,15,C.teal,true);
 bulletLines(s,['Required country and Ladder score fields','Numeric types for all source indicator columns','Unique, nonempty country names','Finite Ladder scores within 0–10'],88,384,470,19,C.ink,39);
 rect(s,630,322,586,242,C.white,C.line);
 text(s,'SOURCE MISSING VALUES',654,344,500,24,15,C.teal,true);
 bulletLines(s,missing,654,384,520,18,C.ink,39);
 text(s,'Correlations use pairwise complete rows. Means use available observations. No rows or outliers were removed.',64,600,1100,40,18,C.muted,true);
 notes(s);
}
// 5 — Tools / methods
{
 const s=base('Tools and methodology');
 text(s,'The workflow keeps source loading, validation, statistics, charts, and dashboard transformations reusable.',64,170,1100,50,24,C.ink);
 const labels=[['Python 3.12','Runtime'],['pandas + NumPy','Load, validate, transform'],['SciPy','Pearson and Spearman tests'],['Matplotlib + Seaborn','Static analysis figures'],['Streamlit + Plotly','Interactive dashboard']];
 labels.forEach((it,i)=>{
   const y=248+i*68;
   text(s,String(i+1).padStart(2,'0'),82,y,48,30,16,C.coral,true);
   text(s,it[0],146,y-4,300,34,23,C.navy,true);
   text(s,it[1],465,y,590,32,20,C.muted);
   rect(s,82,y+42,1040,1,C.line);
 });
 text(s,'Pearson measures linear association. Spearman measures rank-based monotonic association. Both report p-values and pairwise sample sizes.',82,610,1070,42,17,C.muted,true);
 notes(s);
}
// 6 — Rankings
{
 const s=base('Country rankings');
 console.log('Building ranking charts');
 text(s,`Highest: ${highest['Country name']} ${n(highest['Ladder score']).toFixed(3)}     Lowest: ${lowest['Country name']} ${n(lowest['Ladder score']).toFixed(3)}     Gap: ${gap.toFixed(3)}`,
      64,158,1150,38,20,C.ink,true);
 addNativeBar(s,{title:'Top 10 countries',categories:[...top].reverse().map(x=>x['Country name']),
   series:[{name:'Ladder score',values:[...top].reverse().map(x=>n(x['Ladder score'])),fill:C.teal}],
   position:{left:64,top:212,width:554,height:392},direction:'bar',format:'0.000',min:0,max:8});
 console.log('Top chart added');
 addNativeBar(s,{title:'Bottom 10 countries',categories:[...bottom].reverse().map(x=>x['Country name']),
   series:[{name:'Ladder score',values:[...bottom].reverse().map(x=>n(x['Ladder score'])),fill:C.coral}],
   position:{left:646,top:212,width:564,height:392},direction:'bar',format:'0.000',min:0,max:8});
 console.log('Bottom chart added');
 text(s,'Ladder score is the life-evaluation measure used to order countries. The list reports values from the supplied workbook.',64,635,1080,28,16,C.muted);
 notes(s);
}
// 7 — Finland vs India
{
 const s=base('Finland and India');
 const x0=92, y0=220;
 text(s,'FINLAND',x0,y0,440,35,18,C.teal,true); text(s,'INDIA',680,y0,440,35,18,C.coral,true);
 text(s,'#1',x0,278,430,130,92,C.navy,true); text(s,'#118',680,278,430,130,92,C.navy,true);
 text(s,`${n(finland['Ladder score']).toFixed(3)} Ladder score`,x0,421,430,42,28,C.ink,true);
 text(s,`${n(india['Ladder score']).toFixed(3)} Ladder score`,680,421,430,42,28,C.ink,true);
 rect(s,92,500,1010,2,C.line);
 text(s,`Score difference: ${(n(finland['Ladder score'])-n(india['Ladder score'])).toFixed(3)}`,92,530,850,50,28,C.teal,true);
 text(s,'Both ranks and scores are recalculated from the supplied Ladder score column.',92,600,940,34,18,C.muted);
 notes(s);
}
// 8 — correlations
{
 const s=base('Correlation findings');
 console.log('Building correlation chart');
 const sorted=[...correlations].sort((a,b)=>n(b.pearson_r)-n(a.pearson_r));
  text(s,'Correlation heatmap',64,180,560,28,18,C.navy,true);
  s.images.add({blob:await fs.readFile(path.join(ROOT,'outputs','figures','correlation_heatmap.png')),contentType:'image/png',alt:'Pearson correlations between Ladder score and the six available explanatory factors',fit:'contain',position:{left:64,top:212,width:560,height:378}});
 console.log('Correlation chart added');
 text(s,'STATISTICAL DETAIL',680,180,520,26,15,C.teal,true);
  sorted.forEach((r,i)=>{
    const y=218+i*66;
    text(s,r.factor,680,y,525,20,16,C.navy,true);
    text(s,`Pearson r=${n(r.pearson_r).toFixed(3)}  p=${pValue(r.pearson_p_value)}  n=${r.pearson_n}`,680,y+21,525,18,14,C.ink);
    text(s,`Spearman ρ=${n(r.spearman_rho).toFixed(3)}  p=${pValue(r.spearman_p_value)}  n=${r.spearman_n}`,680,y+39,525,18,14,C.ink);
  });
 text(s,positiveText,64,610,1110,24,18,C.navy,true);
 text(s,`${negativeText} ${weakText}`,64,638,1130,22,14,C.muted);
 notes(s,'p-values are two-sided tests as returned by SciPy. Each factor uses its own complete-case sample.');
}
// 9 — group comparison
{
 const s=base('Top 10 versus bottom 10');
 console.log('Building comparison chart');
 const labels=groups.map(r=>r.factor);
 addNativeBar(s,{title:'Mean report components by ranking group',categories:labels,
  series:[{name:'Top 10',values:groups.map(r=>n(r.top10_mean)),fill:C.teal},
          {name:'Bottom 10',values:groups.map(r=>n(r.bottom10_mean)),fill:C.coral}],
  position:{left:64,top:184,width:1144,height:300},direction:'column',hasLegend:true,format:'0.000',min:0,max:2});
 console.log('Comparison chart added');
 text(s,'FACTOR',74,500,650,24,14,C.teal,true); text(s,'TOP − BOTTOM MEAN',856,500,280,24,14,C.teal,true);
 groups.forEach((r,i)=>{
   const yy=528+i*21;
   text(s,r.factor,74,yy,650,19,14,C.ink);
   text(s,n(r.absolute_difference_top_minus_bottom).toFixed(3),856,yy,220,19,14,C.ink);
 });
 text(s,'Bars show both group means; the table adds only the top-minus-bottom difference. Percent differences are omitted because component ratios are not meaningful.',64,662,1080,20,12,C.muted);
 notes(s);
}
// 10 — dashboard
{
 const s=base('Interactive dashboard');
 text(s,'A local Streamlit application loads and validates the same supplied workbook at launch.',64,170,1070,44,23,C.ink);
  text(s,'RANKINGS',86,200,520,28,16,C.teal,true);
  text(s,'Search country names, sort the table, filter the score range, and switch between all countries, top 10, and bottom 10.',86,238,520,82,19,C.ink);
  text(s,'RELATIONSHIPS',86,334,520,28,16,C.teal,true);
  text(s,'Choose any of six factors for a scatter plot. Switch the heatmap between Pearson and Spearman.',86,372,520,76,19,C.ink);
  text(s,'COUNTRY DETAIL AND DATA QUALITY',86,462,520,28,16,C.coral,true);
  text(s,'View country rank, score, component values, and dataset-average differences. Missingness and outlier summaries are available; missing values remain blank.',86,500,520,98,19,C.ink);
  rect(s,660,206,548,380,C.white,C.line);
  text(s,'GENUINE DASHBOARD SCREENSHOT',690,238,488,26,16,C.teal,true,{align:'center'});
  text(s,'SCREENSHOT PLACEHOLDER',690,348,488,32,22,C.muted,true,{align:'center'});
  text(s,'After running Streamlit, capture a real browser screenshot and replace this panel. No screenshot is embedded until a genuine capture is available.',700,398,468,96,17,C.ink,false,{align:'center'});
  text(s,'Dashboard verified in Streamlit AppTest and launched locally.',86,634,1030,26,15,C.muted,true);
 notes(s);
}
// 11 — insights and limits
{
 const s=base('What the results can and cannot say');
 bulletLines(s,[
   positiveText,
   negativeText,
   weakText,
  'Top-10 averages exceed bottom-10 averages across the six available components.',
  'These are country-level associations and report decomposition values, not causal effects.',
  'The workbook provides no region, income category, or annual country series.',
 ],86,190,1080,20,C.ink,60);
 text(s,'The report ranking is a multi-year country summary. It cannot support within-country change analysis or explain why an individual is happier.',86,574,1050,58,20,C.muted,true);
 notes(s);
}
// 12 — conclusion
{
 const s=presentation.slides.add(); s.background.fill=C.navy;
 text(s,'GLOBAL HAPPINESS\nINSIGHTS 2025',82,86,720,120,46,C.white,true);
 rect(s,82,240,86,4,C.coral);
 text(s,`${highest['Country name']} leads with ${n(highest['Ladder score']).toFixed(3)}. ${lowest['Country name']} ranks last with ${n(lowest['Ladder score']).toFixed(3)}.`,82,285,1060,64,26,'#E6EEF1',true);
 text(s,`Finland: rank 1, ${n(finland['Ladder score']).toFixed(3)}     India: rank 118, ${n(india['Ladder score']).toFixed(3)}`,82,380,1080,42,22,'#B9CBD3');
 text(s,'Next steps',82,485,230,30,18,'#60C1B8',true);
 text(s,'Add reliable regional or income metadata for grouped comparisons. Use additional years to study trends. Keep this project’s analysis distinct from the original internship presentation.',82,528,1040,84,21,C.white);
 text(s,'Reconstructed project results · source workbook preserved unchanged',82,648,1020,24,16,'#B9CBD3',true);
  text(s,'Repository: [add URL after publication]  ·  Author: [add name]',82,680,1050,20,14,'#B9CBD3');
 notes(s);
}

// Keep previews and PPTX within the authorized project workspace.
const previewDir=path.join(BUILD,'previews'); await fs.mkdir(previewDir,{recursive:true});
for (let i=0;i<presentation.slides.items.length;i++) {
 const slide=presentation.slides.items[i];
 console.log(`Rendering slide ${i+1}`);
 const png=await presentation.export({slide,format:'png',scale:1});
 await fs.writeFile(path.join(previewDir,`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await png.arrayBuffer()));
}
const draft=path.join(BUILD,'candidate.pptx');
await (await PresentationFile.exportPptx(presentation)).save(draft);
const { finalizePresentation } = await import(pathToFileURL(path.join(TOOLKIT,'container_tools','artifact_tool_utils.mjs')).href);
await fs.mkdir(OUT,{recursive:true});
const result=await finalizePresentation({
  explicitTotalSlideCount:12,
  requiredNativeTableOwnerSlides:[],
  requiredNativeChartOwnerSlides:[6,9],
  workspaceDir:ROOT,
  candidatePath:draft,
  finalPath:STAGED_FINAL,
  pythonExecutable:process.env.PYTHON_EXECUTABLE || 'python',
  integrityValidatorPath:path.join(TOOLKIT,'container_tools','inspect_presentation_package_integrity.py'),
  layoutValidatorPath:path.join(TOOLKIT,'container_tools','inspect_presentation_layout_geometry.py'),
  layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit'],
  fontPolicy:{basis:'design',families:[FONT,'Aptos']},
  materializeLiteralChartWorkbooks:true,
  nativeChartTargetApplication:'powerpoint',
  verifyArtifactToolImport:true,
  receiptPath:path.join(BUILD,`validation-${RUN_ID}.json`),
});
await fs.copyFile(STAGED_FINAL,FINAL);
await fs.rm(STAGE_DIR,{recursive:true,force:true});
console.log(JSON.stringify({final:FINAL,slides:presentation.slides.items.length,result},null,2));
