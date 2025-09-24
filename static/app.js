async function fetchWebhook(){
  const res=await fetch('/webhook-url');
  const js=await res.json();
  document.getElementById('webhookUrl').value = js.url || '';
}
async function fetchAccounts(){
  const res=await fetch('/accounts');
  const js=await res.json();
  const tbody=document.querySelector('#tbl tbody'); tbody.innerHTML='';
  (js.accounts||[]).forEach(acc=>{
    const alive=!!acc.alive;
    const tr=document.createElement('tr');
    tr.innerHTML = `
      <td>${acc.id}</td>
      <td><span class="status-dot ${alive?'alive':'dead'}"></span>${alive?'Online':'Offline'}</td>
      <td>${acc.account}</td>
      <td>${acc.nickname??''}</td>
      <td>${acc.pid??''}</td>
      <td>${acc.created_at??''}</td>
      <td>
        <div class="actions">
          <button data-id="${acc.id}" class="btn-open">Open</button>
          <button data-id="${acc.id}" class="btn-restart">Restart</button>
          <button data-id="${acc.id}" class="btn-stop">Stop</button>
          <button data-id="${acc.id}" class="btn-del">Delete</button>
        </div>
      </td>`;
    tbody.appendChild(tr);
  });
  document.querySelectorAll('.btn-open').forEach(btn=>{
    btn.onclick=async()=>{const id=btn.getAttribute('data-id'); const r=await fetch('/open/'+id,{method:'POST'}); const j=await r.json(); if(!j.ok) alert(j.error||'Open failed'); await fetchAccounts();};
  });
  document.querySelectorAll('.btn-restart').forEach(btn=>{
    btn.onclick=async()=>{const id=btn.getAttribute('data-id'); const r=await fetch('/restart/'+id,{method:'POST'}); const j=await r.json(); if(!j.ok) alert(j.error||'Restart failed'); await fetchAccounts();};
  });
  document.querySelectorAll('.btn-stop').forEach(btn=>{
    btn.onclick=async()=>{const id=btn.getAttribute('data-id'); const r=await fetch('/stop/'+id,{method:'POST'}); const j=await r.json(); if(!j.ok) alert(j.error||'Stop failed'); await fetchAccounts();};
  });
  document.querySelectorAll('.btn-del').forEach(btn=>{
    btn.onclick=async()=>{const id=btn.getAttribute('data-id'); if(!confirm('Delete this account?')) return; const r=await fetch('/delete/'+id,{method:'DELETE'}); const j=await r.json(); if(!j.ok) alert(j.error||'Delete failed'); await fetchAccounts();};
  });
}

document.getElementById('btnCopy').onclick=()=>{
  const el=document.getElementById('webhookUrl'); el.select(); navigator.clipboard.writeText(el.value);
};

document.getElementById('btnAdd').onclick=async()=>{
  const payload={account:document.getElementById('acc').value.trim(), nickname:document.getElementById('nick').value.trim()};
  const res=await fetch('/register',{method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)});
  const js=await res.json();
  if(!js.ok){ alert(js.error||'Register failed'); } else { await fetchAccounts(); document.getElementById('acc').value=''; document.getElementById('nick').value=''; }
};

document.getElementById('btnRefreshLog').onclick=loadLogs;

async function loadLogs(){
  const res=await fetch('/logs');
  const js=await res.json();
  document.getElementById('logs').innerText = (js.logs||[]).join('');
}

(async()=>{
  await fetchWebhook();
  await fetchAccounts();
  await loadLogs();
  setInterval(fetchAccounts, 2000);
})();
