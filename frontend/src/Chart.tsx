import {useEffect,useRef} from 'react';
import * as echarts from 'echarts';
import type {Result} from './types';
export function Chart({result,previous,onSelect}:{result:Result;previous?:Result;onSelect:(id:string)=>void}){
 const ref=useRef<HTMLDivElement>(null);const instance=useRef<echarts.ECharts|null>(null);
 useEffect(()=>{
  const c=echarts.init(ref.current!);instance.current=c;
  const series:echarts.SeriesOption[]=result.traces.map(t=>({name:t.name,type:'line',showSymbol:false,data:result.time_min.map((x,i)=>[x,t.y[i]])}));
  previous?.traces.forEach(t=>series.push({name:'Before · '+t.name,type:'line',showSymbol:false,lineStyle:{type:'dashed',opacity:.5},data:previous.time_min.map((x,i)=>[x,t.y[i]])}));
  series.push({name:'Program %B',type:'line',yAxisIndex:1,showSymbol:false,lineStyle:{type:'dashed',width:1},data:result.time_min.map((x,i)=>[x,result.gradient.program_b_percent[i]])},{name:'Inlet %B',type:'line',yAxisIndex:1,showSymbol:false,lineStyle:{width:1},data:result.time_min.map((x,i)=>[x,result.gradient.inlet_b_percent[i]])});
  c.setOption({color:['#008b8b','#df8a32','#666acd','#a4aeb5','#79a8bb'],animation:false,legend:{type:'scroll',top:0},tooltip:{trigger:'axis'},grid:{left:55,right:48,top:55,bottom:85},xAxis:{type:'value',name:'Time (min)',nameLocation:'middle',nameGap:35},yAxis:[{type:'value',name:'Response (a.u.)'},{type:'value',min:0,max:100,name:'%B',splitLine:{show:false}}],dataZoom:[{type:'inside'},{type:'slider',bottom:8}],series});
  c.on('click',e=>{const t=result.traces.find(t=>t.name===e.seriesName);if(t)onSelect(t.id);});
  const observer=new ResizeObserver(()=>c.resize());observer.observe(ref.current!);return()=>{observer.disconnect();c.dispose();};
 },[result,previous,onSelect]);
 return <div className="chart-block"><div ref={ref} className="chart" data-testid="chromatogram"/><button className="secondary" onClick={()=>{const a=document.createElement('a');a.href=instance.current!.getDataURL({pixelRatio:2,backgroundColor:'#fff'});a.download='EluSim-chromatogram.png';a.click();}}>Export PNG</button><span className="muted">Pinch / scroll to zoom · Tap legend to hide peaks</span></div>;
}
