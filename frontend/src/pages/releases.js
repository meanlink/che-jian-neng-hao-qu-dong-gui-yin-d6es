import {releases,versions} from '../api/entities.js';
import {workspace} from '../stores/workspace.js';
import {session} from '../stores/session.js';
import {heading} from '../components/common/shell.js';
import {VersionStatus} from '../constants/enums.js';
import {esc,fmt,date,notify} from '../utils/dom.js';
import {submit} from '../hooks/forms.js';
const chip=v=>'<span class="status '+esc(v)+'">'+esc(VersionStatus[v]||v)+'</span>';
const nameOf=(list,id)=>{const v=list.find(x=>x.id===id);return v?esc(v.name):'—';};
function versionCard(v,admin){
 const s=v.summary||{},actions=[];
 if(admin&&v.status==='pending')actions.push('<span class="inline-ratio"><input type="number" min="1" max="100" value="10" id="ratio-'+v.id+'">%</span><button class="button small" data-publish="'+v.id+'">发布为灰度</button>');
 if(admin&&v.status==='canary')actions.push('<button class="button small" data-promote="'+v.id+'">推广为正式</button>');
 if(admin&&v.status==='pending')actions.push('<button class="button small" data-promote="'+v.id+'">直接推广为正式</button>');
 if(admin&&v.status==='retired')actions.push('<button class="button small" data-rollback="'+v.id+'">回滚为正式</button>');
 actions.push('<button class="text-button" data-artifact="'+v.id+'">计算依据 ↓</button>');
 return '<article class="version-card '+esc(v.status)+'"><div class="version-head">'+chip(v.status)+'<strong>'+esc(v.name)+'</strong><span class="version-id">#'+v.id+'</span></div><p>'+(s.features?'入选特征 '+esc(s.features.join('、'))+' · α='+esc(fmt(s.alpha))+' · 留出验证RMSE '+esc(fmt(s.validation&&s.validation.rmse))+' kWh':'')+'</p><small>来源试验 #'+v.job_id+' '+esc(s.source_job||'')+' · 封存 '+date(v.created_at)+' · SHA256 '+esc((v.checksum||'').slice(0,20))+'…</small>'+(v.note?'<p class="note">'+esc(v.note)+'</p>':'')+'<div class="version-actions">'+actions.join('')+'</div></article>';
}
export async function releasePage(){
 const [state,sealable]=await Promise.all([releases.state(),releases.sealable()]);workspace.release=state;
 const c=state.config,list=state.versions,admin=session.user.role==='admin';
 const candidates=sealable.filter(j=>!j.sealed);
 const configPanel='<section class="panel"><div class="section-title"><h2>当前发布配置</h2><span>一次性切换 · 已接纳单沿用原版</span></div><div class="release-config"><div><span>正式版</span><strong>'+nameOf(list,c.active_version_id)+'</strong></div><div><span>灰度版</span><strong>'+nameOf(list,c.canary_version_id)+'</strong></div><div><span>灰度比例</span><strong>'+c.canary_ratio+'%</strong></div></div>'+(c.canary_version_id?'<form id="ratio-form" class="ratio-form"><label>调整灰度比例 %<input type="number" name="ratio" min="0" max="100" step="1" value="'+c.canary_ratio+'" required></label><button type="submit" class="primary" '+(admin?'':'disabled')+'>保存比例</button></form>':'<p class="hint">当前无灰度版本。发布灰度后可在此调整分流比例，新排产单立即按新比例分流。</p>')+'<p class="hint">最近变更 '+esc(c.updated_by||'—')+' · '+(c.updated_at?date(c.updated_at):'—')+'</p></section>';
 const sealForm='<section class="panel"><div class="section-title"><h2>封存预测版本</h2></div><form id="seal-form"><label>版本名称<input name="name" required minlength="2" value="预测版本 · 冲压P01"></label><label>已批准试验<select name="job_id" required>'+candidates.map(j=>'<option value="'+j.id+'">'+esc(j.name)+'</option>').join('')+'</select></label><label>封存备注<input name="note" maxlength="200" placeholder="上线口径、数据来源说明"></label><button type="submit" class="primary" '+(admin&&candidates.length?'':'disabled')+'>封存为待校验版本</button></form><p class="hint">封存即固化完整计算依据（特征、标准化参数、系数、验证误差），生成独立版本文件与校验和，之后重训不影响本版本。仅负责人可封存。</p></section>';
 const artifact=workspace.artifactView;
 const artifactPanel=artifact?'<section class="panel"><div class="section-title"><h2>版本 #'+artifact.id+' 计算依据</h2><span>SHA256 '+esc((artifact.data.version.checksum||'').slice(0,24))+'…</span></div><pre class="artifact-view">'+esc(JSON.stringify(artifact.data.model,null,2))+'</pre></section>':'';
 return heading('06 / RELEASE','版本发布与灰度','已批准试验封存为不可变预测版本；按排产单号稳定分流到正式版或灰度版，推广与回滚一次性切换。','<button class="button" id="refresh-releases">刷新状态 ↻</button>')+'<div class="release-grid"><section>'+configPanel+sealForm+'</section><section><div class="section-title"><h2>版本台账</h2><span>'+list.length+' 个版本 · 待校验/灰度中/正式/退役</span></div><div class="version-list">'+list.map(v=>versionCard(v,admin)).join('')+'</div>'+artifactPanel+'</section></div>';
}
export function bindReleases(refresh){
 const rerender=async()=>{workspace.artifactView=null;await refresh();};
 document.querySelector('#refresh-releases').onclick=rerender;
 const ratioForm=document.querySelector('#ratio-form');if(ratioForm)submit(ratioForm,async f=>{await releases.setRatio(Number(f.get('ratio')));notify('灰度比例已更新，新排产单按新比例分流');await rerender();});
 const sealForm=document.querySelector('#seal-form');if(sealForm)submit(sealForm,async f=>{await versions.seal({name:f.get('name'),job_id:Number(f.get('job_id')),note:f.get('note')||''});notify('已封存为待校验版本');await rerender();});
 document.querySelectorAll('[data-publish]').forEach(b=>b.onclick=async()=>{try{const ratio=Number(document.querySelector('#ratio-'+b.dataset.publish).value);await versions.publish(b.dataset.publish,ratio);notify('已发布为灰度版');await rerender();}catch(e){notify(e.message,true);}});
 document.querySelectorAll('[data-promote]').forEach(b=>b.onclick=async()=>{try{await versions.promote(b.dataset.promote);notify('已推广为正式版，旧版退役');await rerender();}catch(e){notify(e.message,true);}});
 document.querySelectorAll('[data-rollback]').forEach(b=>b.onclick=async()=>{try{await versions.rollback(b.dataset.rollback);notify('已回滚为正式版');await rerender();}catch(e){notify(e.message,true);}});
 document.querySelectorAll('[data-artifact]').forEach(b=>b.onclick=async()=>{try{const data=await versions.artifact(b.dataset.artifact);workspace.artifactView={id:b.dataset.artifact,data};await refresh();}catch(e){notify(e.message,true);}});
}
