// Touch-first fluid Canva ordering. Only reorder the user's chosen IDs; never edit event data.
// The moving card is a GPU-composited visual clone. Real rows are rearranged with FLIP animation.
export function orderedCanvaIds(list){
  return Array.from(list.children).filter(row=>row.matches('.canva-item')).map(row=>row.dataset.id);
}
export function insertionIndexForPointer(midpoints,y){
  const n=midpoints.findIndex(mid=>y<mid);
  return n<0?midpoints.length:n;
}
export function createFluidCanvaSorter({list,scrollArea,onCommit,onCancel}){
  let active=null;
  const reduceMotion=()=>window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
  function placeAtPointer(y){
    if(!active)return;
    const item=active.item;
    const peers=Array.from(list.children).filter(row=>row!==item);
    const index=insertionIndexForPointer(peers.map(row=>{
      const b=row.getBoundingClientRect();return b.top+b.height/2;
    }),y);
    const before=peers[index]||null;
    if(before===item.nextElementSibling || (!before && item===list.lastElementChild))return;
    // Snapshot the currently animated on-screen position first, then cancel
    // stale animations BEFORE measuring the new layout: prevents FLIP jitter.
    const oldY=new Map(peers.map(row=>[row,row.getBoundingClientRect().top]));
    for(const row of peers)row._canvaFlip?.cancel();
    list.insertBefore(item,before);
    if(reduceMotion())return;
    for(const row of peers){
      const delta=oldY.get(row)-row.getBoundingClientRect().top;
      if(Math.abs(delta)<0.5)continue;
      row._canvaFlip=row.animate(
        [{transform:'translate3d(0,'+delta+'px,0)'},{transform:'translate3d(0,0,0)'}],
        {duration:145,easing:'cubic-bezier(.2,.75,.3,1)'}
      );
    }
  }
  function scrollFrame(){
    if(!active)return;
    const b=scrollArea.getBoundingClientRect();
    const edge=Math.min(74,b.height*.22);
    let velocity=0;
    if(active.y<b.top+edge)velocity=-Math.min(18,((b.top+edge-active.y)/edge)*18);
    else if(active.y>b.bottom-edge)velocity=Math.min(18,((active.y-(b.bottom-edge))/edge)*18);
    if(velocity){
      const old=scrollArea.scrollTop;
      scrollArea.scrollTop+=velocity;
      if(scrollArea.scrollTop!==old)placeAtPointer(active.y);
    }
    active.frame=requestAnimationFrame(scrollFrame);
  }
  function finish(commit){
    if(!active)return;
    const d=active;
    active=null;
    cancelAnimationFrame(d.frame);
    try{if(d.handle.hasPointerCapture?.(d.pointerId))d.handle.releasePointerCapture(d.pointerId);}catch{}
    d.ghost.remove();
    d.item.classList.remove('canva-is-placeholder');
    document.documentElement.classList.remove('canva-is-sorting');
    const after=orderedCanvaIds(list);
    const changed=after.some((id,i)=>id!==d.before[i]);
    if(!commit){
      if(changed)onCancel();
    }else if(changed){
      onCommit(after,{from:d.before.indexOf(d.id)+1,to:after.indexOf(d.id)+1});
    }
  }
  list.addEventListener('pointerdown',e=>{
    const handle=e.target.closest('.canva-drag-handle');
    if(!handle || active || (e.pointerType==='mouse'&&e.button!==0))return;
    const item=handle.closest('.canva-item');
    if(!item||!list.contains(item))return;
    e.preventDefault();
    const b=item.getBoundingClientRect(),ghost=item.cloneNode(true);
    ghost.removeAttribute('id');
    ghost.classList.add('canva-drag-ghost');
    ghost.style.left=b.left+'px';
    ghost.style.top=b.top+'px';
    ghost.style.width=b.width+'px';
    ghost.style.height=b.height+'px';
    document.body.appendChild(ghost);
    active={
      item,handle,ghost,id:item.dataset.id,
      pointerId:e.pointerId,startY:e.clientY,y:e.clientY,
      before:orderedCanvaIds(list),frame:0
    };
    item.classList.add('canva-is-placeholder');
    document.documentElement.classList.add('canva-is-sorting');
    try{handle.setPointerCapture(e.pointerId);}catch{}
    active.frame=requestAnimationFrame(scrollFrame);
  });
  list.addEventListener('pointermove',e=>{
    if(!active||e.pointerId!==active.pointerId)return;
    e.preventDefault();
    active.y=e.clientY;
    active.ghost.style.transform='translate3d(0,'+(e.clientY-active.startY)+'px,0)';
    placeAtPointer(e.clientY);
  });
  list.addEventListener('pointerup',e=>{
    if(active&&e.pointerId===active.pointerId){e.preventDefault();finish(true);}
  });
  list.addEventListener('pointercancel',e=>{
    if(active&&e.pointerId===active.pointerId)finish(false);
  });
  // Keyboard and assistive-technology fallback: keep the handle focusable.
  list.addEventListener('keydown',e=>{
    if(!e.target.closest('.canva-drag-handle'))return;
    if(e.key!=='ArrowUp'&&e.key!=='ArrowDown')return;
    const item=e.target.closest('.canva-item');
    const before=orderedCanvaIds(list),from=before.indexOf(item?.dataset.id);
    const to=from+(e.key==='ArrowUp'?-1:1);
    if(from<0||to<0||to>=before.length)return;
    e.preventDefault();
    const after=[...before],moved=after.splice(from,1)[0];after.splice(to,0,moved);
    onCommit(after,{from:from+1,to:to+1,focusId:item.dataset.id});
  });
  return {cancel:()=>finish(false)};
}
