import {api} from './client.js';
export const datasets={list:()=>api('/datasets'),get:id=>api('/datasets/'+id),create:data=>api('/datasets',{method:'POST',body:JSON.stringify(data)})};
export const jobs={list:()=>api('/jobs'),get:id=>api('/jobs/'+id),create:data=>api('/jobs',{method:'POST',body:JSON.stringify(data)}),approve:id=>api('/jobs/'+id+'/approve',{method:'POST'})};
export const reports={list:()=>api('/reports'),create:data=>api('/reports',{method:'POST',body:JSON.stringify(data)}),toggle:id=>api('/reports/'+id+'/toggle',{method:'POST'}),deliveries:()=>api('/deliveries')};
export const releases={state:()=>api('/releases'),sealable:()=>api('/versions/sealable/jobs'),setRatio:ratio=>api('/releases/ratio',{method:'POST',body:JSON.stringify({ratio})})};
export const versions={seal:data=>api('/versions',{method:'POST',body:JSON.stringify(data)}),publish:(id,ratio)=>api('/versions/'+id+'/publish',{method:'POST',body:JSON.stringify({ratio})}),promote:id=>api('/versions/'+id+'/promote',{method:'POST'}),rollback:id=>api('/versions/'+id+'/rollback',{method:'POST'}),artifact:id=>api('/versions/'+id+'/artifact')};
export const predictions={list:()=>api('/predictions'),get:id=>api('/predictions/'+id),create:data=>api('/predictions',{method:'POST',body:JSON.stringify(data)})};
