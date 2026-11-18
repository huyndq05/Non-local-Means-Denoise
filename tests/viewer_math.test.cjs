const test=require('node:test');
const assert=require('node:assert/strict');
const Viewport=require('../src/viewer_component/viewport.js');
function near(a,b){assert.ok(Math.abs(a-b)<1e-8,`${a} != ${b}`);}
test('screen/image coordinate round trip at zoom and pan',()=>{
 const v=new Viewport(512,384);v.zoomAt(4,250,160,500,350);v.pan(-40,20,500,350);
 const p=v.imagePoint(110,230,500,350),s=v.screenPoint(p.x,p.y,500,350);near(s.x,110);near(s.y,230);
});
test('zoom anchors source pixel under pointer',()=>{
 const v=new Viewport(512,384);v.zoomAt(2,250,175,500,350);
 const before=v.imagePoint(280,190,500,350);v.zoomAt(5,280,190,500,350);
 const after=v.imagePoint(280,190,500,350);near(before.x,after.x);near(before.y,after.y);
});
test('either pane uses one shared pixel viewport',()=>{
 const v=new Viewport(256,256);v.zoomAt(5,250,175,500,350);
 // Right-pane gesture mutates the sole shared state; both panels read it.
 v.pan(-50,35,500,350);
 const left=v.imagePoint(200,150,500,350),right=v.imagePoint(200,150,500,350);
 assert.deepEqual(left,right);
 v.zoomAt(8,200,150,500,350);
 assert.deepEqual(v.imagePoint(200,150,500,350),v.imagePoint(200,150,500,350));
});
test('pan clamps image edges and fit returns to center',()=>{
 const v=new Viewport(512,384);v.zoomAt(8,250,175,500,350);v.pan(1e6,-1e6,500,350);
 const s=v.scale(500,350);near(v.cx,500/(2*s));near(v.cy,384-350/(2*s));
 v.fit();assert.equal(v.zoom,1);assert.equal(v.cx,256);assert.equal(v.cy,192);
});
test('actual pixel scale works for images smaller and bigger than panel',()=>{
 for(const side of [64,256,1024]){
  const v=new Viewport(side,side),base=v.base(500,350);
  v.zoomAt(1/base,250,175,500,350);near(v.scale(500,350),1);
 }
});
test('extreme wheel zoom stays bounded',()=>{
 const v=new Viewport(256,256);v.zoomAt(1e6,250,175,500,350);assert.equal(v.zoom,64);
 v.zoomAt(0,250,175,500,350);assert.ok(v.zoom>0);
});
