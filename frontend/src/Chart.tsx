import {useEffect,useRef} from 'react';
import * as echarts from 'echarts';
import type {Result} from './types';
export function Chart({result,previous,onSelect}:{result:Result;previous?:Result;onSelect:(id:string)=>void}){
 const ref=useRef<HTMLDivElement>(null);const instance=useRef<echarts.ECharts|null>(null);
 useEffect(()=>{
  const c=echarts.init(ref.current!);instance.current=c;
  const series:echarts.SeriesOption[]=result.traces.map(t=>{const peak=result.peaks.find(p=>p.id===t.id);return {id:t.id,name:t.name,type:'line',showSymbol:false,data:result.time_min.map((x,i)=>[x,t.y[i]]),markLine:peak?.rt_min!=null?{silent:true,symbol:'none',label:{formatter:peak.rt_min.toFixed(3)+' min',position:'insideEndTop',rotate:90,fontSize:10},lineStyle:{type:'dotted'},data:[{xAxis:peak.rt_min}]}:undefined};});
  series.push({id:'total-signal',name:'Total simulated signal',type:'line',showSymbol:false,itemStyle:{color:'#253e45'},lineStyle:{width:2,color:'#253e45'},data:result.time_min.map((x,i)=>[x,result.traces.reduce((sum,t)=>sum+t.y[i],0)])});
  previous?.traces.forEach(t=>series.push({id:'before-'+t.id,name:'Before · '+t.name,type:'line',showSymbol:false,lineStyle:{type:'dashed',opacity:.5},data:previous.time_min.map((x,i)=>[x,t.y[i]])}));
  c.setOption({color:['#008b8b','#df8a32','#666acd'],animation:false,legend:{type:'scroll',top:0},tooltip:{trigger:'axis'},grid:{left:65,right:25,top:65,bottom:85},xAxis:{type:'value',name:'Retention Time (min)',nameLocation:'middle',nameGap:35},yAxis:{type:'value',name:'Relative Response (a.u.)',nameLocation:'middle',nameGap:45},dataZoom:[{type:'inside'},{type:'slider',bottom:8}],series});
  c.on('click',e=>{const t=result.traces.find(t=>t.id===e.seriesId);if(t)onSelect(t.id);});
  const observer=new ResizeObserver(()=>c.resize());observer.observe(ref.current!);return()=>{observer.disconnect();c.dispose();};
 },[result,previous,onSelect]);
 return <div className="chart-block"><div ref={ref} className="chart" data-testid="chromatogram" role="img" aria-label="Simulated Chromatogram: Retention Time (min), Relative Response (a.u.); compound peaks and total signal"/><button className="secondary" onClick={()=>{const a=document.createElement('a');a.href=instance.current!.getDataURL({pixelRatio:2,backgroundColor:'#fff'});a.download='EluSim-chromatogram.png';a.click();}}>Export PNG</button><span className="muted">Pinch / scroll to zoom · Tap legend to hide peaks</span></div>;
}
export function GradientProfile({result}:{result:Result}){
 const ref=useRef<HTMLDivElement>(null);const instance=useRef<echarts.ECharts|null>(null);
 useEffect(()=>{const c=echarts.init(ref.current!);instance.current=c;c.setOption({animation:false,legend:{top:0},tooltip:{trigger:'axis'},grid:{left:55,right:25,top:45,bottom:55},xAxis:{type:'value',name:'Time (min)',nameLocation:'middle',nameGap:30},yAxis:{type:'value',name:'%B',min:0,max:100},series:[{name:'Programmed %B',type:'line',showSymbol:false,lineStyle:{type:'dashed'},data:result.time_min.map((x,i)=>[x,result.gradient.program_b_percent[i]])},{name:'Column Inlet %B',type:'line',showSymbol:false,data:result.time_min.map((x,i)=>[x,result.gradient.inlet_b_percent[i]])}]});const observer=new ResizeObserver(()=>c.resize());observer.observe(ref.current!);return()=>{observer.disconnect();c.dispose();};},[result]);
 return <details className="gradient-profile" onToggle={e=>{if(e.currentTarget.open)requestAnimationFrame(()=>instance.current?.resize());}}><summary>Gradient Profile — programmed / column inlet</summary><p className="muted">Dwell volume {result.input.mobile.dwell_ml} mL; initial delay {(result.input.mobile.dwell_ml/result.input.gradient[0].flow_ml_min).toFixed(3)} min. Variable-flow delay follows transported volume. This profile is an input check, not evidence of successful separation.</p><div className="chart" ref={ref} data-testid="gradient-profile" role="img" aria-label="Gradient Profile: Programmed and Column Inlet percent B"/></details>;
}
