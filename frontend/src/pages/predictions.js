import {predictions} from '../api/entities.js';
import {workspace} from '../stores/workspace.js';
import {session} from '../stores/session.js';
import {heading} from '../components/common/shell.js';
import {table} from '../components/common/table.js';
import {VersionStatus,Lane} from '../constants/enums.js';
import {esc,fmt,date,notify} from '../utils/dom.js';
import {submit} from '../hooks/forms.js';
const SAMPLE='2026-11-18,800,12,20,2\n2026-11-19,850,12.5,21,1.5\n2026-11-20,780,11.8,19,2.2';
function parseItems(text){
 return text.split('\n').map(l=>l.trim()).filter(Boolean).map((l,i)=>{
  const p=l.split(/[,，\s]+/);
  if(p.length!==5||p.some(x=>x===''))throw new Error('第'+(i+1)+'行需要 5 列：日期,日产量,运行小时,温度,待机小时');
  const [day,units,run_hours,temp_c,idle_hours]=p,nums=[units,run_hours,temp_c,idle_hours].map(Number);
  if(nums.some(Number.isNaN))throw new Error('第'+(i+1)+'行包含非数值列');
  return {day,units:nums[0],run_hours:nums[1],temp_c:nums[2],idle_hours:nums[3]};
 });
}
function detailView(o){
 const itemRows=o.items.map(i=>({...i,inputs:'产量 '+fmt(i.inputs.units)+' · 运行 '+fmt(i.inputs.run_hours)+'h · 温度 '+fmt(i.inputs.temp_c)+'℃ · 待机 '+fmt(i.inputs.idle_hours)+'h',flags:(i.flags||[]).join('、')||'—'}));
 return '<section class="panel result-lead"><p class="eyebrow">PREDICTION RESULT</p><h2>排产单 '+esc(o.order_no)+' 共 '+o.item_count+' 天，预测总电耗 '+esc(fmt(o.total_kwh))+' kWh</h2><div class="metrics"><div><span>预测版本</span><strong>#'+o.version_id+'<small>'+esc(o.version?o.version.name:'')+'</small></strong></div><div><span>分流通道</span><strong>'+esc(Lane[o.lane]||o.lane)+'<small>'+esc(o.version?(VersionStatus[o.version.status]||o.version.status):'')+'</small></strong></div><div><span>受理时间</span><strong class="metric-time">'+date(o.created_at)+'</strong></div>'+(o.replayed?'<div><span>重试重放</span><strong>是<small>未重复计算</small></strong></div>':'')+'</div><p class="hint">版本校验和 '+esc(o.version?o.version.checksum:'—')+'</p></section><section class="panel"><div class="section-title"><h2>预测明细</h2><span>版本 · 输入 · 日电耗可追溯</span></div>'+table([{key:'day',label:'日期'},{key:'inputs',label:'排产输入'},{key:'kwh',label:'预测日电耗 kWh'},{key:'flags',label:'标记'}],itemRows,'暂无明细')+'</section>';
}
export async function predictionPage(id){
 const list=await predictions.list();workspace.orders=list;
 let detail=null;
 if(id){detail=await predictions.get(id);}
 else if(workspace.lastPrediction){detail=workspace.lastPrediction;}
 const canWrite=session.user.role!=='viewer';
 const form='<section class="panel"><div class="section-title"><h2>提交排产单</h2></div><form id="predict-form"><label>排产单号<input name="order_no" required minlength="2" maxlength="64" placeholder="如 SC-2026-1101" value="SC-2026-'+String(Date.now()).slice(-6)+'"></label><label>排产明细（每行：日期,日产量,运行小时,温度℃,待机小时）<textarea name="items" rows="6" required>'+SAMPLE+'</textarea></label><button type="submit" class="primary" '+(canWrite?'':'disabled')+'>预测整单日电耗 ↗</button></form><p class="hint">整单固定一个版本：按单号稳定分流到正式版或灰度版。中断后重试同一单号与内容直接返回原结果，不重复预测、不改换版本；同号异内容将被拒绝。</p></section>';
 const ordersPanel='<section><div class="section-title"><h2>已接纳排产单</h2><span>'+list.length+' 单</span></div><div class="order-list">'+list.map(o=>'<a class="order-row" href="#/predictions/'+o.id+'"><strong>'+esc(o.order_no)+'</strong><span>#'+o.version_id+' '+esc(o.version_name)+'</span><span class="status '+esc(o.lane)+'">'+esc(Lane[o.lane]||o.lane)+'</span><span>'+o.item_count+' 天 · '+esc(fmt(o.total_kwh))+' kWh</span><small>'+date(o.created_at)+'</small></a>').join('')+'</div><p class="hint">点击单号查看版本、输入与日电耗明细。</p></section>';
 return heading('07 / PREDICTION','排产日电耗预测','排产系统按单号提交整单，直接获得每日电耗预测；版本、输入与结果全程可追溯。','<button class="button" id="refresh-predictions">刷新列表 ↻</button>')+'<div class="predict-grid"><section>'+form+ordersPanel+'</section><section>'+(detail?detailView(detail):'<div class="empty">提交排产单或从左侧选择已接纳单，查看预测明细。</div>')+'</section></div>';
}
export function bindPredictions(refresh){
 document.querySelector('#refresh-predictions').onclick=refresh;
 submit(document.querySelector('#predict-form'),async f=>{
  const items=parseItems(f.get('items'));
  const o=await predictions.create({order_no:f.get('order_no').trim(),items});
  workspace.lastPrediction=o;
  notify(o.replayed?'该单已受理，返回原预测结果':'预测完成，整单使用版本 #'+o.version_id);
  location.hash='#/predictions/'+o.id;
 });
}
