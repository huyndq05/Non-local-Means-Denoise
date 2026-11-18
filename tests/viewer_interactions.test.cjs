// Unit harness for actual event handlers; no browser or server dependencies.
const test=require('node:test'),assert=require('node:assert/strict');
const vm=require('node:vm'),fs=require('node:fs');
const Viewport=require('../src/viewer_component/viewport.js');
function harness(){
 const elements={},handlers={},posts=[];
 for(const id of ['left','right','zoom','zoomLabel','lens','status','root','leftTitle','rightTitle','in','out','fit','actual']){
  const events={},draws=[],arcs=[];
  const ctx={setTransform(){},clearRect(){draws.length=0;arcs.length=0;},drawImage(...args){draws.push(args);},
   save(){},restore(){},beginPath(){},arc(...args){arcs.push(args);},clip(){},fillRect(){},stroke(){},moveTo(){},lineTo(){}};
  elements[id]={clientWidth:500,clientHeight:350,scrollHeight:490,width:500,height:350,checked:true,
   style:{setProperty(){}},classList:{add(){},remove(){}},focus(){},setPointerCapture(){},
   getBoundingClientRect(){return {left:0,top:0};},getContext(){return ctx;},
   addEventListener(name,fn){events[name]=fn;},events,draws,arcs};
 }
 const parent={postMessage(message){posts.push(message);}};
 const window={parent,devicePixelRatio:1,addEventListener(name,fn){handlers[name]=fn;}};
 const document={getElementById(id){return elements[id];},documentElement:{style:{setProperty(){}}}};
 class FakeImage{set src(src){this.source=src;this.naturalWidth=256;this.naturalHeight=256;queueMicrotask(()=>this.onload());}}
 const sandbox={window,document,NLMViewport:Viewport,Image:FakeImage,ResizeObserver:class{observe(){}},
   getComputedStyle(){return {getPropertyValue(){return '#ffffff';}};},console};
 vm.runInNewContext(fs.readFileSync(require.resolve('../src/viewer_component/viewer.js'),'utf8'),sandbox);
 const event=(extra={})=>({clientX:250,clientY:175,button:0,pointerId:1,preventDefault(){},...extra});
 const render=(left='noisy',right='method1')=>handlers.message({source:parent,data:{type:'streamlit:render',args:{left,right,image_width:256,image_height:256,left_title:'Left',right_title:'Right'}}});
 function sameGeometry(){
  const a=elements.left,b=elements.right;
  assert.deepEqual(a.draws.map(x=>x.slice(1)),b.draws.map(x=>x.slice(1)));
  assert.deepEqual(a.arcs,b.arcs);
 }
 return {elements,posts,event,render,sameGeometry};
}
test('wheel/drag/lens on either panel redraw both with identical geometry',async()=>{
 const h=harness();await h.render();h.sameGeometry();
 const {left,right}=h.elements;
 const fit=left.draws[0].slice(1);
 right.events.wheel(h.event({deltaY:-550,deltaMode:0}));h.sameGeometry();assert.notDeepEqual(left.draws[0].slice(1),fit);
 assert.equal(left.draws.length,2);assert.equal(right.draws.length,2); // lens and main image
 right.events.pointerdown(h.event());
 right.events.pointermove(h.event({clientX:280,clientY:190}));h.sameGeometry();
 right.events.pointerup(h.event());
 left.events.pointermove(h.event({clientX:230,clientY:170}));h.sameGeometry();
 const geometry=left.draws.map(x=>x.slice(1));
 await h.render('noisy','method2');h.sameGeometry();assert.deepEqual(left.draws.map(x=>x.slice(1)),geometry);
 await h.render('new_noisy','method2');h.sameGeometry();assert.deepEqual(left.draws[0].slice(1),fit);
 assert.ok(h.posts.some(p=>p.type==='streamlit:componentReady'));
 assert.ok(h.posts.some(p=>p.type==='streamlit:setFrameHeight'&&p.height>0));
});
test('fit and actual-pixel buttons plus keyboard are wired to the shared viewport',async()=>{
 const h=harness();await h.render();
 h.elements.actual.onclick();h.sameGeometry();assert.equal(h.elements.left.draws[0][3],256);
 h.elements.right.events.keydown(h.event({key:'+'}));h.sameGeometry();
 h.elements.right.events.keydown(h.event({key:'ArrowRight'}));h.sameGeometry();
 h.elements.fit.onclick();h.sameGeometry();assert.equal(h.elements.left.draws[0][3],350);
});
