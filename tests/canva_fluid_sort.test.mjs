import assert from 'node:assert/strict';
import {test} from 'node:test';
import {createFluidCanvaSorter,orderedCanvaIds,insertionIndexForPointer} from '../site/canva-fluid-sort.js';

test('touch drag reorders on drop, cancels without storage changes, and autoscrolls',()=>{
  const old={window:globalThis.window,document:globalThis.document,raf:globalThis.requestAnimationFrame,caf:globalThis.cancelAnimationFrame};
  let scheduled=null,frameId=0;
  const cl=()=>({add(){},remove(){},toggle(){},contains(){return false;}});
  const root={classList:cl()};
  const documentBody={appendChild(){}};
  const scrollArea={scrollTop:0,getBoundingClientRect(){return {top:70,bottom:260,height:190};}};
  let commits=[],cancelCount=0,animations=0;
  const handlers={};
  const rows=[];
  const list={
    children:rows,
    addEventListener(event,callback){handlers[event]=callback;},
    contains(node){return rows.includes(node);},
    insertBefore(node,before){
      rows.splice(rows.indexOf(node),1);
      rows.splice(rows.indexOf(before),0,node);
    },
    appendChild(node){rows.splice(rows.indexOf(node),1);rows.push(node);},
    get lastElementChild(){return rows.at(-1);}
  };
  function item(id){
    const row={
      dataset:{id},classList:cl(),
      matches(selector){return selector==='.canva-item';},
      get nextElementSibling(){return rows[rows.indexOf(this)+1]||null;},
      getBoundingClientRect(){const top=70+rows.indexOf(this)*34-scrollArea.scrollTop;return {left:5,top,width:250,height:32};},
      cloneNode(){return {classList:cl(),style:{},removeAttribute(){},remove(){}};},
      animate(){animations++;return {cancel(){}};}
    };
    const handle={
      closest(selector){
        if(selector==='.canva-drag-handle')return handle;
        if(selector==='.canva-item')return row;
        return null;
      },
      setPointerCapture(pointerId){this.capture=pointerId;},
      hasPointerCapture(pointerId){return this.capture===pointerId;},
      releasePointerCapture(){this.capture=null;}
    };
    row.handle=handle;
    return row;
  }
  rows.push(item('a'),item('b'),item('c'),item('d'));
  const fire=(name,target,y=0,id=7)=>handlers[name]({target,clientY:y,pointerId:id,pointerType:'touch',preventDefault(){},button:0});
  try{
    globalThis.window={matchMedia:()=>({matches:false})};
    globalThis.document={body:documentBody,documentElement:root};
    globalThis.requestAnimationFrame=fn=>{scheduled=fn;return ++frameId;};
    globalThis.cancelAnimationFrame=()=>{};
    createFluidCanvaSorter({
      list,scrollArea,
      onCommit:(ids,move)=>{commits.push({ids,move});},
      onCancel:()=>{cancelCount++;}
    });
    assert.deepEqual(orderedCanvaIds(list),['a','b','c','d']);
    assert.equal(insertionIndexForPointer([86,120,154],155),3);
    fire('pointerdown',rows[1].handle,120);
    fire('pointermove',rows[1].handle,245);
    assert.deepEqual(orderedCanvaIds(list),['a','c','d','b']);
    assert.ok(animations>0,'neighboring cards animate as the dragged card crosses them');
    assert.ok(scheduled);
    scheduled();
    assert.ok(scrollArea.scrollTop>0,'drag near the bottom should auto-scroll the list');
    fire('pointerup',rows[3].handle,245);
    assert.equal(commits.length,1,'persist after drop, not on pointermove');
    assert.deepEqual(commits[0].ids,['a','c','d','b']);
    assert.deepEqual(commits[0].move,{from:2,to:4});
    fire('pointerdown',rows[3].handle,245);
    fire('pointermove',rows[3].handle,74);
    fire('pointercancel',rows[0].handle,74);
    assert.equal(commits.length,1,'cancel must never save');
    assert.equal(cancelCount,1,'cancel requests the caller to restore the last saved order');
  }finally{
    globalThis.window=old.window;
    globalThis.document=old.document;
    globalThis.requestAnimationFrame=old.raf;
    globalThis.cancelAnimationFrame=old.caf;
  }
});
