(function(){
  const canvases=[document.getElementById('left'),document.getElementById('right')];
  const slider=document.getElementById('zoom'),label=document.getElementById('zoomLabel');
  const lens=document.getElementById('lens'),status=document.getElementById('status');
  let viewport=null,images=[],hover=null,drag=null,oldLeft=null,renderId=0,disabled=false;
  function send(type,extra={}){window.parent.postMessage({isStreamlitMessage:true,type,...extra},'*');}
  function frame(){send('streamlit:setFrameHeight',{height:document.getElementById('root').scrollHeight+8});}
  function size(canvas){return {w:canvas.clientWidth,h:canvas.clientHeight};}
  function point(canvas,event){const r=canvas.getBoundingClientRect();return {x:event.clientX-r.left,y:event.clientY-r.top};}
  function repaint(){
    if(!viewport||images.length!==2)return;
    canvases.forEach((canvas,index)=>{
      const {w,h}=size(canvas);if(w<=0||h<=0)return;
      const dpr=window.devicePixelRatio||1;
      if(canvas.width!==Math.round(w*dpr)||canvas.height!==Math.round(h*dpr)){canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);}
      const ctx=canvas.getContext('2d');ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);
      const scale=viewport.scale(w,h),x=w/2-viewport.cx*scale,y=h/2-viewport.cy*scale;
      ctx.imageSmoothingEnabled=scale<1;
      ctx.drawImage(images[index],x,y,viewport.width*scale,viewport.height*scale);
      if(hover&&lens.checked){
        const q=viewport.screenPoint(hover.x,hover.y,w,h),r=Math.min(70,w*.2,h*.25),mag=scale*3;
        ctx.save();ctx.beginPath();ctx.arc(q.x,q.y,r,0,2*Math.PI);ctx.clip();
        ctx.fillStyle=getComputedStyle(document.documentElement).getPropertyValue('--surface');ctx.fillRect(q.x-r,q.y-r,2*r,2*r);
        ctx.imageSmoothingEnabled=false;
        ctx.drawImage(images[index],q.x-hover.x*mag,q.y-hover.y*mag,viewport.width*mag,viewport.height*mag);
        ctx.restore();ctx.beginPath();ctx.arc(q.x,q.y,r,0,2*Math.PI);ctx.strokeStyle='#00d4cf';ctx.lineWidth=2.5;ctx.stroke();
        ctx.strokeStyle='#00d4cf';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(q.x-8,q.y);ctx.lineTo(q.x+8,q.y);ctx.moveTo(q.x,q.y-8);ctx.lineTo(q.x,q.y+8);ctx.stroke();
      }
    });
    const {w,h}=size(canvases[0]);
    slider.min=Math.min(1,1/viewport.base(w,h));slider.value=viewport.zoom;label.textContent=viewport.zoom.toFixed(2)+'×';
    status.textContent=`Hai ảnh đồng bộ · ${viewport.width} × ${viewport.height} px · ${Math.round(viewport.scale(w,h)*100)}% kích thước pixel`+
      (hover?` · Con trỏ: x=${Math.floor(hover.x)}, y=${Math.floor(hover.y)}`+(lens.checked?' · kính lúp thêm 3×':''):'');
  }
  function zoom(value,canvas=canvases[0],p=null){
    if(!viewport||disabled)return;const {w,h}=size(canvas);p=p||{x:w/2,y:h/2};viewport.zoomAt(value,p.x,p.y,w,h);repaint();
  }
  function updateHover(canvas,p){const {w,h}=size(canvas),q=viewport.imagePoint(p.x,p.y,w,h);hover=q.x>=0&&q.y>=0&&q.x<viewport.width&&q.y<viewport.height?q:null;}
  for(const canvas of canvases){
    canvas.addEventListener('wheel',event=>{
      if(!viewport||disabled)return;event.preventDefault();const p=point(canvas,event);
      zoom(viewport.zoom*Math.exp(-event.deltaY*(event.deltaMode===1?.045:.002)),canvas,p);updateHover(canvas,p);repaint();
    },{passive:false});
    canvas.addEventListener('pointerdown',event=>{
      if(!viewport||disabled||event.button!==0)return;
      canvas.focus({preventScroll:true});canvas.setPointerCapture(event.pointerId);
      drag={canvas,id:event.pointerId,...point(canvas,event)};canvas.classList.add('dragging');
    });
    canvas.addEventListener('pointermove',event=>{
      if(!viewport||disabled)return;const p=point(canvas,event),{w,h}=size(canvas);
      if(drag&&drag.canvas===canvas&&drag.id===event.pointerId){viewport.pan(p.x-drag.x,p.y-drag.y,w,h);drag.x=p.x;drag.y=p.y;}
      updateHover(canvas,p);repaint();
    });
    function end(event){if(drag&&drag.canvas===canvas&&drag.id===event.pointerId){drag=null;canvas.classList.remove('dragging');}}
    canvas.addEventListener('pointerup',end);canvas.addEventListener('pointercancel',end);canvas.addEventListener('lostpointercapture',end);
    canvas.addEventListener('pointerleave',()=>{if(!drag){hover=null;repaint();}});
    canvas.addEventListener('dblclick',()=>{if(viewport){viewport.fit();hover=null;repaint();}});
    canvas.addEventListener('keydown',event=>{
      if(!viewport||disabled)return;const {w,h}=size(canvas);let handled=true;
      if(event.key==='+'||event.key==='=')zoom(viewport.zoom*1.25,canvas);
      else if(event.key==='-')zoom(viewport.zoom/1.25,canvas);
      else if(event.key.startsWith('Arrow')){
        const dx=event.key==='ArrowLeft'?35:event.key==='ArrowRight'?-35:0;
        const dy=event.key==='ArrowUp'?35:event.key==='ArrowDown'?-35:0;
        viewport.pan(dx,dy,w,h);hover=null;repaint();
      }else handled=false;
      if(handled)event.preventDefault();
    });
  }
  slider.addEventListener('input',()=>zoom(Number(slider.value)));
  document.getElementById('in').onclick=()=>viewport&&zoom(viewport.zoom*1.5);
  document.getElementById('out').onclick=()=>viewport&&zoom(viewport.zoom/1.5);
  document.getElementById('fit').onclick=()=>{if(viewport){viewport.fit();hover=null;repaint();}};
  document.getElementById('actual').onclick=()=>{if(viewport){const {w,h}=size(canvases[0]);zoom(1/viewport.base(w,h));}};
  lens.onchange=repaint;
  function load(src){return new Promise((resolve,reject)=>{const im=new Image();im.onload=()=>resolve(im);im.onerror=reject;im.src=src;});}
  window.addEventListener('message',async event=>{
    if(event.source!==window.parent||event.data.type!=='streamlit:render')return;
    const {args,theme}=event.data;disabled=!!event.data.disabled;
    if(theme){const style=document.documentElement.style;style.setProperty('--bg',theme.backgroundColor);style.setProperty('--surface',theme.secondaryBackgroundColor);style.setProperty('--text',theme.textColor);style.setProperty('--accent',theme.primaryColor);}
    document.getElementById('leftTitle').textContent=args.left_title;
    document.getElementById('rightTitle').textContent=args.right_title;
    const token=++renderId;
    try{
      const loaded=await Promise.all([load(args.left),load(args.right)]);if(token!==renderId)return;
      if(loaded.some(im=>im.naturalWidth!==args.image_width||im.naturalHeight!==args.image_height))throw Error('Ảnh không cùng kích thước');
      if(!viewport||oldLeft!==args.left){viewport=new NLMViewport(args.image_width,args.image_height);hover=null;drag=null;}
      oldLeft=args.left;images=loaded;repaint();frame();
    }catch(error){status.textContent='Không tải được cặp ảnh để so sánh. Hãy chạy lại hoặc tải lại trang.';frame();}
  });
  new ResizeObserver(()=>{if(viewport){const {w,h}=size(canvases[0]);if(w&&h)viewport.clamp(w,h);}repaint();frame();}).observe(document.getElementById('root'));
  send('streamlit:componentReady',{apiVersion:1});frame();
})();
