/* Pixel coordinates are shared by both panels, never separate transforms. */
(function(root) {
  class Viewport {
    constructor(width,height) { this.width=width;this.height=height;this.cx=width/2;this.cy=height/2;this.zoom=1; }
    base(cw,ch) { return Math.min(cw/this.width,ch/this.height); }
    scale(cw,ch) { return this.base(cw,ch)*this.zoom; }
    imagePoint(x,y,cw,ch) {
      const s=this.scale(cw,ch);
      return {x:this.cx+(x-cw/2)/s,y:this.cy+(y-ch/2)/s};
    }
    screenPoint(x,y,cw,ch) {
      const s=this.scale(cw,ch);
      return {x:cw/2+(x-this.cx)*s,y:ch/2+(y-this.cy)*s};
    }
    clamp(cw,ch) {
      const s=this.scale(cw,ch),hx=Math.min(this.width/2,cw/(2*s)),hy=Math.min(this.height/2,ch/(2*s));
      this.cx=Math.max(hx,Math.min(this.width-hx,this.cx));
      this.cy=Math.max(hy,Math.min(this.height-hy,this.cy));
    }
    zoomAt(zoom,x,y,cw,ch) {
      const before=this.imagePoint(x,y,cw,ch);
      this.zoom=Math.max(Math.min(1,1/this.base(cw,ch)),Math.min(64,zoom));
      const after=this.imagePoint(x,y,cw,ch);
      this.cx+=before.x-after.x;this.cy+=before.y-after.y;this.clamp(cw,ch);
    }
    pan(dx,dy,cw,ch) {const s=this.scale(cw,ch);this.cx-=dx/s;this.cy-=dy/s;this.clamp(cw,ch);}
    fit() {this.zoom=1;this.cx=this.width/2;this.cy=this.height/2;}
  }
  root.NLMViewport=Viewport;
  if(typeof module!=='undefined') module.exports=Viewport;
})(typeof window!=='undefined'?window:globalThis);
