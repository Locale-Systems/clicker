function t(t,e,i,s){var n,r=arguments.length,a=r<3?e:null===s?s=Object.getOwnPropertyDescriptor(e,i):s;if("object"==typeof Reflect&&"function"==typeof Reflect.decorate)a=Reflect.decorate(t,e,i,s);else for(var o=t.length-1;o>=0;o--)(n=t[o])&&(a=(r<3?n(a):r>3?n(e,i,a):n(e,i))||a);return r>3&&a&&Object.defineProperty(e,i,a),a}"function"==typeof SuppressedError&&SuppressedError;const e=globalThis,i=e.ShadowRoot&&(void 0===e.ShadyCSS||e.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,s=Symbol(),n=new WeakMap;let r=class{constructor(t,e,i){if(this._$cssResult$=!0,i!==s)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=e}get styleSheet(){let t=this.o;const e=this.t;if(i&&void 0===t){const i=void 0!==e&&1===e.length;i&&(t=n.get(e)),void 0===t&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),i&&n.set(e,t))}return t}toString(){return this.cssText}};const a=(t,...e)=>{const i=1===t.length?t[0]:e.reduce((e,i,s)=>e+(t=>{if(!0===t._$cssResult$)return t.cssText;if("number"==typeof t)return t;throw Error("Value passed to 'css' function must be a 'css' function result: "+t+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(i)+t[s+1],t[0]);return new r(i,t,s)},o=i?t=>t:t=>t instanceof CSSStyleSheet?(t=>{let e="";for(const i of t.cssRules)e+=i.cssText;return(t=>new r("string"==typeof t?t:t+"",void 0,s))(e)})(t):t,{is:d,defineProperty:c,getOwnPropertyDescriptor:l,getOwnPropertyNames:h,getOwnPropertySymbols:p,getPrototypeOf:u}=Object,m=globalThis,v=m.trustedTypes,g=v?v.emptyScript:"",_=m.reactiveElementPolyfillSupport,f=(t,e)=>t,$={toAttribute(t,e){switch(e){case Boolean:t=t?g:null;break;case Object:case Array:t=null==t?t:JSON.stringify(t)}return t},fromAttribute(t,e){let i=t;switch(e){case Boolean:i=null!==t;break;case Number:i=null===t?null:Number(t);break;case Object:case Array:try{i=JSON.parse(t)}catch(t){i=null}}return i}},b=(t,e)=>!d(t,e),y={attribute:!0,type:String,converter:$,reflect:!1,useDefault:!1,hasChanged:b};Symbol.metadata??=Symbol("metadata"),m.litPropertyMetadata??=new WeakMap;let x=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??=[]).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,e=y){if(e.state&&(e.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((e=Object.create(e)).wrapped=!0),this.elementProperties.set(t,e),!e.noAccessor){const i=Symbol(),s=this.getPropertyDescriptor(t,i,e);void 0!==s&&c(this.prototype,t,s)}}static getPropertyDescriptor(t,e,i){const{get:s,set:n}=l(this.prototype,t)??{get(){return this[e]},set(t){this[e]=t}};return{get:s,set(e){const r=s?.call(this);n?.call(this,e),this.requestUpdate(t,r,i)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??y}static _$Ei(){if(this.hasOwnProperty(f("elementProperties")))return;const t=u(this);t.finalize(),void 0!==t.l&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(f("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(f("properties"))){const t=this.properties,e=[...h(t),...p(t)];for(const i of e)this.createProperty(i,t[i])}const t=this[Symbol.metadata];if(null!==t){const e=litPropertyMetadata.get(t);if(void 0!==e)for(const[t,i]of e)this.elementProperties.set(t,i)}this._$Eh=new Map;for(const[t,e]of this.elementProperties){const i=this._$Eu(t,e);void 0!==i&&this._$Eh.set(i,t)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){const e=[];if(Array.isArray(t)){const i=new Set(t.flat(1/0).reverse());for(const t of i)e.unshift(o(t))}else void 0!==t&&e.push(o(t));return e}static _$Eu(t,e){const i=e.attribute;return!1===i?void 0:"string"==typeof i?i:"string"==typeof t?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(t=>t(this))}addController(t){(this._$EO??=new Set).add(t),void 0!==this.renderRoot&&this.isConnected&&t.hostConnected?.()}removeController(t){this._$EO?.delete(t)}_$E_(){const t=new Map,e=this.constructor.elementProperties;for(const i of e.keys())this.hasOwnProperty(i)&&(t.set(i,this[i]),delete this[i]);t.size>0&&(this._$Ep=t)}createRenderRoot(){const t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return((t,s)=>{if(i)t.adoptedStyleSheets=s.map(t=>t instanceof CSSStyleSheet?t:t.styleSheet);else for(const i of s){const s=document.createElement("style"),n=e.litNonce;void 0!==n&&s.setAttribute("nonce",n),s.textContent=i.cssText,t.appendChild(s)}})(t,this.constructor.elementStyles),t}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(t=>t.hostConnected?.())}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach(t=>t.hostDisconnected?.())}attributeChangedCallback(t,e,i){this._$AK(t,i)}_$ET(t,e){const i=this.constructor.elementProperties.get(t),s=this.constructor._$Eu(t,i);if(void 0!==s&&!0===i.reflect){const n=(void 0!==i.converter?.toAttribute?i.converter:$).toAttribute(e,i.type);this._$Em=t,null==n?this.removeAttribute(s):this.setAttribute(s,n),this._$Em=null}}_$AK(t,e){const i=this.constructor,s=i._$Eh.get(t);if(void 0!==s&&this._$Em!==s){const t=i.getPropertyOptions(s),n="function"==typeof t.converter?{fromAttribute:t.converter}:void 0!==t.converter?.fromAttribute?t.converter:$;this._$Em=s;const r=n.fromAttribute(e,t.type);this[s]=r??this._$Ej?.get(s)??r,this._$Em=null}}requestUpdate(t,e,i,s=!1,n){if(void 0!==t){const r=this.constructor;if(!1===s&&(n=this[t]),i??=r.getPropertyOptions(t),!((i.hasChanged??b)(n,e)||i.useDefault&&i.reflect&&n===this._$Ej?.get(t)&&!this.hasAttribute(r._$Eu(t,i))))return;this.C(t,e,i)}!1===this.isUpdatePending&&(this._$ES=this._$EP())}C(t,e,{useDefault:i,reflect:s,wrapped:n},r){i&&!(this._$Ej??=new Map).has(t)&&(this._$Ej.set(t,r??e??this[t]),!0!==n||void 0!==r)||(this._$AL.has(t)||(this.hasUpdated||i||(e=void 0),this._$AL.set(t,e)),!0===s&&this._$Em!==t&&(this._$Eq??=new Set).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(t){Promise.reject(t)}const t=this.scheduleUpdate();return null!=t&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(const[t,e]of this._$Ep)this[t]=e;this._$Ep=void 0}const t=this.constructor.elementProperties;if(t.size>0)for(const[e,i]of t){const{wrapped:t}=i,s=this[e];!0!==t||this._$AL.has(e)||void 0===s||this.C(e,void 0,i,s)}}let t=!1;const e=this._$AL;try{t=this.shouldUpdate(e),t?(this.willUpdate(e),this._$EO?.forEach(t=>t.hostUpdate?.()),this.update(e)):this._$EM()}catch(e){throw t=!1,this._$EM(),e}t&&this._$AE(e)}willUpdate(t){}_$AE(t){this._$EO?.forEach(t=>t.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&=this._$Eq.forEach(t=>this._$ET(t,this[t])),this._$EM()}updated(t){}firstUpdated(t){}};x.elementStyles=[],x.shadowRootOptions={mode:"open"},x[f("elementProperties")]=new Map,x[f("finalized")]=new Map,_?.({ReactiveElement:x}),(m.reactiveElementVersions??=[]).push("2.1.2");const w=globalThis,A=t=>t,k=w.trustedTypes,S=k?k.createPolicy("lit-html",{createHTML:t=>t}):void 0,E="$lit$",C=`lit$${Math.random().toFixed(9).slice(2)}$`,P="?"+C,O=`<${P}>`,M=document,z=()=>M.createComment(""),N=t=>null===t||"object"!=typeof t&&"function"!=typeof t,R=Array.isArray,U="[ \t\n\f\r]",T=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,H=/-->/g,D=/>/g,j=RegExp(`>|${U}(?:([^\\s"'>=/]+)(${U}*=${U}*(?:[^ \t\n\f\r"'\`<>=]|("|')|))|$)`,"g"),I=/'/g,L=/"/g,B=/^(?:script|style|textarea|title)$/i,q=(t=>(e,...i)=>({_$litType$:t,strings:e,values:i}))(1),W=Symbol.for("lit-noChange"),V=Symbol.for("lit-nothing"),F=new WeakMap,K=M.createTreeWalker(M,129);function J(t,e){if(!R(t)||!t.hasOwnProperty("raw"))throw Error("invalid template strings array");return void 0!==S?S.createHTML(e):e}const Z=(t,e)=>{const i=t.length-1,s=[];let n,r=2===e?"<svg>":3===e?"<math>":"",a=T;for(let e=0;e<i;e++){const i=t[e];let o,d,c=-1,l=0;for(;l<i.length&&(a.lastIndex=l,d=a.exec(i),null!==d);)l=a.lastIndex,a===T?"!--"===d[1]?a=H:void 0!==d[1]?a=D:void 0!==d[2]?(B.test(d[2])&&(n=RegExp("</"+d[2],"g")),a=j):void 0!==d[3]&&(a=j):a===j?">"===d[0]?(a=n??T,c=-1):void 0===d[1]?c=-2:(c=a.lastIndex-d[2].length,o=d[1],a=void 0===d[3]?j:'"'===d[3]?L:I):a===L||a===I?a=j:a===H||a===D?a=T:(a=j,n=void 0);const h=a===j&&t[e+1].startsWith("/>")?" ":"";r+=a===T?i+O:c>=0?(s.push(o),i.slice(0,c)+E+i.slice(c)+C+h):i+C+(-2===c?e:h)}return[J(t,r+(t[i]||"<?>")+(2===e?"</svg>":3===e?"</math>":"")),s]};class Y{constructor({strings:t,_$litType$:e},i){let s;this.parts=[];let n=0,r=0;const a=t.length-1,o=this.parts,[d,c]=Z(t,e);if(this.el=Y.createElement(d,i),K.currentNode=this.el.content,2===e||3===e){const t=this.el.content.firstChild;t.replaceWith(...t.childNodes)}for(;null!==(s=K.nextNode())&&o.length<a;){if(1===s.nodeType){if(s.hasAttributes())for(const t of s.getAttributeNames())if(t.endsWith(E)){const e=c[r++],i=s.getAttribute(t).split(C),a=/([.?@])?(.*)/.exec(e);o.push({type:1,index:n,name:a[2],strings:i,ctor:"."===a[1]?et:"?"===a[1]?it:"@"===a[1]?st:tt}),s.removeAttribute(t)}else t.startsWith(C)&&(o.push({type:6,index:n}),s.removeAttribute(t));if(B.test(s.tagName)){const t=s.textContent.split(C),e=t.length-1;if(e>0){s.textContent=k?k.emptyScript:"";for(let i=0;i<e;i++)s.append(t[i],z()),K.nextNode(),o.push({type:2,index:++n});s.append(t[e],z())}}}else if(8===s.nodeType)if(s.data===P)o.push({type:2,index:n});else{let t=-1;for(;-1!==(t=s.data.indexOf(C,t+1));)o.push({type:7,index:n}),t+=C.length-1}n++}}static createElement(t,e){const i=M.createElement("template");return i.innerHTML=t,i}}function G(t,e,i=t,s){if(e===W)return e;let n=void 0!==s?i._$Co?.[s]:i._$Cl;const r=N(e)?void 0:e._$litDirective$;return n?.constructor!==r&&(n?._$AO?.(!1),void 0===r?n=void 0:(n=new r(t),n._$AT(t,i,s)),void 0!==s?(i._$Co??=[])[s]=n:i._$Cl=n),void 0!==n&&(e=G(t,n._$AS(t,e.values),n,s)),e}class Q{constructor(t,e){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){const{el:{content:e},parts:i}=this._$AD,s=(t?.creationScope??M).importNode(e,!0);K.currentNode=s;let n=K.nextNode(),r=0,a=0,o=i[0];for(;void 0!==o;){if(r===o.index){let e;2===o.type?e=new X(n,n.nextSibling,this,t):1===o.type?e=new o.ctor(n,o.name,o.strings,this,t):6===o.type&&(e=new nt(n,this,t)),this._$AV.push(e),o=i[++a]}r!==o?.index&&(n=K.nextNode(),r++)}return K.currentNode=M,s}p(t){let e=0;for(const i of this._$AV)void 0!==i&&(void 0!==i.strings?(i._$AI(t,i,e),e+=i.strings.length-2):i._$AI(t[e])),e++}}class X{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(t,e,i,s){this.type=2,this._$AH=V,this._$AN=void 0,this._$AA=t,this._$AB=e,this._$AM=i,this.options=s,this._$Cv=s?.isConnected??!0}get parentNode(){let t=this._$AA.parentNode;const e=this._$AM;return void 0!==e&&11===t?.nodeType&&(t=e.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,e=this){t=G(this,t,e),N(t)?t===V||null==t||""===t?(this._$AH!==V&&this._$AR(),this._$AH=V):t!==this._$AH&&t!==W&&this._(t):void 0!==t._$litType$?this.$(t):void 0!==t.nodeType?this.T(t):(t=>R(t)||"function"==typeof t?.[Symbol.iterator])(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==V&&N(this._$AH)?this._$AA.nextSibling.data=t:this.T(M.createTextNode(t)),this._$AH=t}$(t){const{values:e,_$litType$:i}=t,s="number"==typeof i?this._$AC(t):(void 0===i.el&&(i.el=Y.createElement(J(i.h,i.h[0]),this.options)),i);if(this._$AH?._$AD===s)this._$AH.p(e);else{const t=new Q(s,this),i=t.u(this.options);t.p(e),this.T(i),this._$AH=t}}_$AC(t){let e=F.get(t.strings);return void 0===e&&F.set(t.strings,e=new Y(t)),e}k(t){R(this._$AH)||(this._$AH=[],this._$AR());const e=this._$AH;let i,s=0;for(const n of t)s===e.length?e.push(i=new X(this.O(z()),this.O(z()),this,this.options)):i=e[s],i._$AI(n),s++;s<e.length&&(this._$AR(i&&i._$AB.nextSibling,s),e.length=s)}_$AR(t=this._$AA.nextSibling,e){for(this._$AP?.(!1,!0,e);t!==this._$AB;){const e=A(t).nextSibling;A(t).remove(),t=e}}setConnected(t){void 0===this._$AM&&(this._$Cv=t,this._$AP?.(t))}}class tt{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,e,i,s,n){this.type=1,this._$AH=V,this._$AN=void 0,this.element=t,this.name=e,this._$AM=s,this.options=n,i.length>2||""!==i[0]||""!==i[1]?(this._$AH=Array(i.length-1).fill(new String),this.strings=i):this._$AH=V}_$AI(t,e=this,i,s){const n=this.strings;let r=!1;if(void 0===n)t=G(this,t,e,0),r=!N(t)||t!==this._$AH&&t!==W,r&&(this._$AH=t);else{const s=t;let a,o;for(t=n[0],a=0;a<n.length-1;a++)o=G(this,s[i+a],e,a),o===W&&(o=this._$AH[a]),r||=!N(o)||o!==this._$AH[a],o===V?t=V:t!==V&&(t+=(o??"")+n[a+1]),this._$AH[a]=o}r&&!s&&this.j(t)}j(t){t===V?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}}class et extends tt{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===V?void 0:t}}class it extends tt{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==V)}}class st extends tt{constructor(t,e,i,s,n){super(t,e,i,s,n),this.type=5}_$AI(t,e=this){if((t=G(this,t,e,0)??V)===W)return;const i=this._$AH,s=t===V&&i!==V||t.capture!==i.capture||t.once!==i.once||t.passive!==i.passive,n=t!==V&&(i===V||s);s&&this.element.removeEventListener(this.name,this,i),n&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){"function"==typeof this._$AH?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t)}}class nt{constructor(t,e,i){this.element=t,this.type=6,this._$AN=void 0,this._$AM=e,this.options=i}get _$AU(){return this._$AM._$AU}_$AI(t){G(this,t)}}const rt=w.litHtmlPolyfillSupport;rt?.(Y,X),(w.litHtmlVersions??=[]).push("3.3.3");const at=globalThis;class ot extends x{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){const t=super.createRenderRoot();return this.renderOptions.renderBefore??=t.firstChild,t}update(t){const e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=((t,e,i)=>{const s=i?.renderBefore??e;let n=s._$litPart$;if(void 0===n){const t=i?.renderBefore??null;s._$litPart$=n=new X(e.insertBefore(z(),t),t,void 0,i??{})}return n._$AI(t),n})(e,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return W}}ot._$litElement$=!0,ot.finalized=!0,at.litElementHydrateSupport?.({LitElement:ot});const dt=at.litElementPolyfillSupport;dt?.({LitElement:ot}),(at.litElementVersions??=[]).push("4.2.2");const ct=t=>(e,i)=>{void 0!==i?i.addInitializer(()=>{customElements.define(t,e)}):customElements.define(t,e)},lt={attribute:!0,type:String,converter:$,reflect:!1,hasChanged:b},ht=(t=lt,e,i)=>{const{kind:s,metadata:n}=i;let r=globalThis.litPropertyMetadata.get(n);if(void 0===r&&globalThis.litPropertyMetadata.set(n,r=new Map),"setter"===s&&((t=Object.create(t)).wrapped=!0),r.set(i.name,t),"accessor"===s){const{name:s}=i;return{set(i){const n=e.get.call(this);e.set.call(this,i),this.requestUpdate(s,n,t,!0,i)},init(e){return void 0!==e&&this.C(s,void 0,t,e),e}}}if("setter"===s){const{name:s}=i;return function(i){const n=this[s];e.call(this,i),this.requestUpdate(s,n,t,!0,i)}}throw Error("Unsupported decorator location: "+s)};function pt(t){return(e,i)=>"object"==typeof i?ht(t,e,i):((t,e,i)=>{const s=e.hasOwnProperty(i);return e.constructor.createProperty(i,t),s?Object.getOwnPropertyDescriptor(e,i):void 0})(t,e,i)}function ut(t){return pt({...t,state:!0,attribute:!1})}function mt(t){const e=t?.message;return"string"==typeof e&&e?e:"Something went wrong. Try again."}function vt(t){return`${(t/1e6).toFixed(2)} MHz`}function gt(t,e){const i=vt(e);return t?t.includes(i)?t:`${t} · ${i}`:i}function _t(t){if(!t)return"Not created";switch(t.state){case"unavailable":return"Unavailable";case"on":{const e=t.attributes.percentage;return"number"==typeof e?`On, ${e}%`:"On"}case"off":return"Off";default:return t.entity_id.startsWith("button.")?"":t.state}}const ft={button:"Button",toggle:"Toggle",state:"State"},$t={button:"Always sent; no state",toggle:"Flips the state; sent only to change it",state:"Sets one state; safe to resend"};function bt(t){const e=new Set,i=[];for(const s of t){const t=`${s.bindingName} (${s.platform})`;e.has(t)||(e.add(t),i.push(t))}return i.join(", ")}const yt=a`
  :host {
    color: var(--primary-text-color);
    font-family: var(--ha-font-family-body, Roboto, sans-serif);
  }
  .card {
    background: var(--card-background-color);
    border-radius: var(--ha-card-border-radius, 12px);
    border: 1px solid var(--divider-color);
    padding: 14px 16px;
  }
  .card-title {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 16px;
    font-weight: 500;
    margin-bottom: 8px;
  }
  .meta {
    color: var(--secondary-text-color);
    font-size: 13px;
  }
  button {
    font: inherit;
    font-size: 14px;
    color: var(--primary-color);
    background: none;
    border: 1px solid var(--divider-color);
    border-radius: 8px;
    padding: 6px 12px;
    cursor: pointer;
  }
  button:hover {
    background: var(--secondary-background-color);
  }
  button.primary {
    color: var(--text-primary-color, white);
    background: var(--primary-color);
    border-color: var(--primary-color);
  }
  button.danger {
    color: var(--error-color);
  }
  button.icon {
    border: none;
    padding: 6px;
    color: var(--secondary-text-color);
    display: inline-flex;
  }
  button:disabled {
    opacity: 0.5;
    cursor: default;
  }
  input,
  select {
    font: inherit;
    font-size: 14px;
    color: var(--primary-text-color);
    background: var(--secondary-background-color, transparent);
    border: 1px solid var(--divider-color);
    border-radius: 8px;
    padding: 7px 10px;
    box-sizing: border-box;
  }
  label {
    display: flex;
    flex-direction: column;
    gap: 4px;
    font-size: 13px;
    color: var(--secondary-text-color);
  }
  .chip {
    font-size: 12px;
    padding: 1px 8px;
    border-radius: 10px;
    border: 1px solid var(--divider-color);
    color: var(--secondary-text-color);
    white-space: nowrap;
  }
  .chip.warning {
    color: var(--warning-color);
    border-color: var(--warning-color);
  }
  ha-icon {
    --mdc-icon-size: 20px;
  }
`;let xt=class extends ot{constructor(){super(...arguments),this._saved=new Map}connectedCallback(){super.connectedCallback(),this._unsubscribe=this.hass.connection.subscribeMessage(t=>{this._update=t},{type:"clicker/learn/subscribe",device_id:this.device.id}),this._unsubscribe.catch(t=>this._error=mt(t))}disconnectedCallback(){super.disconnectedCallback(),this._unsubscribe?.then(t=>t()).catch(()=>{}),this._unsubscribe=void 0}_toast(t){this.dispatchEvent(new CustomEvent("hass-notification",{detail:{message:t},bubbles:!0,composed:!0}))}_close(){this.dispatchEvent(new CustomEvent("close"))}async _test(t){if(this._update){this._testing=t.fingerprint;try{await(e=this.hass,i=this._update.session_id,s=t.fingerprint,e.connection.sendMessagePromise({type:"clicker/learn/test",session_id:i,fingerprint:s})),this._toast("Sent. Did the device respond?")}catch(t){this._toast(mt(t))}var e,i,s;this._testing=void 0}}_startSave(t){this._draft={fingerprint:t.fingerprint,mode:"new",name:"",kind:"button",commandId:this.device.commands[0]?.id??""}}_nameTaken(t){return this.device.commands.some(e=>e.name.toLowerCase()===t.trim().toLowerCase())}async _save(){const t=this._draft;if(!t||!this._update)return;const e="new"===t.mode?{name:t.name.trim(),kind:t.kind}:{command_id:t.commandId};try{const i=await((t,e,i,s)=>t.connection.sendMessagePromise({type:"clicker/learn/save",session_id:e,fingerprint:i,...s}))(this.hass,this._update.session_id,t.fingerprint,e);this._saved=new Map([...this._saved,[t.fingerprint,i.name]]),this._draft=void 0,this._toast("new"===t.mode?`Saved ${i.name}`:`Relearned ${i.name}`)}catch(t){this._toast(mt(t))}}render(){const t=this._update?vt(this._update.frequency_hz):vt(this.device.frequency_hz),e=this._update?.candidates??[];return q`
      <div class="card learning">
        <div class="card-title">
          Learn <span class="spacer"></span>
          <button class="icon" aria-label="Stop learning" @click=${this._close}>
            <ha-icon icon="mdi:close"></ha-icon>
          </button>
        </div>
        ${this._error?q`<div class="error">${this._error}</div>`:q`<div class="listening">
              <span class="dot"></span>
              ${this._update?`Listening on ${t}. Press a button on the remote 2 or 3 times.`:"Starting…"}
            </div>`}
        ${e.map(t=>this._renderCandidate(t))}
      </div>
    `}_renderCandidate(t){const e=this._saved.get(t.fingerprint),i=t.known_as.find(t=>t.device===this.device.name),s=t.known_as.filter(t=>t.device!==this.device.name),n=this._draft?.fingerprint===t.fingerprint;return q`
      <div class="candidate">
        <div class="candidate-head">
          <span class="candidate-title">${function(t){if(!t.bits)return"Raw code";const e=t.bits.slice(-8);return`${t.bits.length}-bit code ${t.bits.length>8?"…":""}${e}`}(t)}</span>
          ${e?q`<span class="chip success">Saved as ${e}</span>`:i?q`<span class="chip warning">Already ${i.command}</span>`:q`<span class="chip">New</span>`}
        </div>
        <div class="meta">${function(t){const e=[t.usable?t.encoded?"Encoded":"Raw replay":"Too short to use",`seen ${t.sightings}×`];return t.variants>1&&e.push(`${t.variants} variants`),e.join(" · ")}(t)}</div>
        ${s.length?q`<div class="meta">
              Also sent by ${s.map(t=>`${t.device} / ${t.command}`).join(", ")}
            </div>`:V}
        ${n?this._renderDraft(this._draft):t.usable?q`<div class="actions">
                <button
                  ?disabled=${this._testing===t.fingerprint}
                  @click=${()=>this._test(t)}
                >
                  ${this._testing===t.fingerprint?"Sending…":"Test"}
                </button>
                ${e?V:q`<button @click=${()=>this._startSave(t)}>Save…</button>`}
              </div>`:V}
      </div>
    `}_renderDraft(t){const e=e=>this._draft={...t,...e},i="new"===t.mode&&this._nameTaken(t.name),s="new"===t.mode?!!t.name.trim()&&!i:!!t.commandId;return q`
      <div class="draft">
        <div class="modes">
          <label class="radio"
            ><input
              type="radio"
              name="mode"
              .checked=${"new"===t.mode}
              @change=${()=>e({mode:"new"})}
            />New command</label
          >
          ${this.device.commands.length?q`<label class="radio"
                ><input
                  type="radio"
                  name="mode"
                  .checked=${"replace"===t.mode}
                  @change=${()=>e({mode:"replace"})}
                />Relearn an existing one</label
              >`:V}
        </div>
        ${"new"===t.mode?q`<label
                >Name
                <input
                  placeholder="Light"
                  .value=${t.name}
                  @input=${t=>e({name:t.target.value})}
                />
                ${i?q`<span class="hint error">${this.device.name} already has one</span>`:V}
              </label>
              <label
                >Kind
                <select @change=${t=>e({kind:t.target.value})}>
                  ${Object.entries(ft).map(([e,i])=>q`<option value=${e} ?selected=${e===t.kind}>
                      ${i}
                    </option>`)}
                </select>
                <span class="hint">${$t[t.kind]}</span>
              </label>`:q`<label
              >Replace the code of
              <select @change=${t=>e({commandId:t.target.value})}>
                ${this.device.commands.map(e=>q`<option value=${e.id} ?selected=${e.id===t.commandId}>${e.name}</option>`)}
              </select>
            </label>`}
        <div class="actions">
          <span class="spacer"></span>
          <button @click=${()=>this._draft=void 0}>Cancel</button>
          <button class="primary" ?disabled=${!s} @click=${this._save}>
            ${"new"===t.mode?"Save":"Relearn"}
          </button>
        </div>
      </div>
    `}};xt.styles=[yt,a`
      .learning {
        border-color: var(--primary-color);
      }
      .spacer {
        flex: 1;
      }
      .listening {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 14px;
        color: var(--secondary-text-color);
        margin-bottom: 8px;
      }
      .dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: var(--primary-color);
        animation: pulse 1.6s ease-in-out infinite;
      }
      @keyframes pulse {
        50% {
          opacity: 0.25;
        }
      }
      .error {
        color: var(--error-color);
        font-size: 14px;
      }
      .candidate {
        border: 1px solid var(--divider-color);
        border-radius: 8px;
        padding: 10px 12px;
        margin-top: 8px;
      }
      .candidate-head {
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .candidate-title {
        flex: 1;
        font-weight: 500;
        font-family: var(--code-font-family, monospace);
        font-size: 14px;
      }
      .chip.success {
        color: var(--success-color);
        border-color: var(--success-color);
      }
      .actions {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-top: 8px;
      }
      .draft {
        display: flex;
        flex-direction: column;
        gap: 10px;
        margin-top: 10px;
      }
      .modes {
        display: flex;
        gap: 16px;
        flex-wrap: wrap;
      }
      label.radio {
        flex-direction: row;
        align-items: center;
        gap: 6px;
        font-size: 14px;
        color: var(--primary-text-color);
      }
      .hint {
        font-size: 12px;
        color: var(--secondary-text-color);
      }
      .hint.error {
        color: var(--error-color);
      }
    `],t([pt({attribute:!1})],xt.prototype,"hass",void 0),t([pt({attribute:!1})],xt.prototype,"device",void 0),t([ut()],xt.prototype,"_update",void 0),t([ut()],xt.prototype,"_error",void 0),t([ut()],xt.prototype,"_draft",void 0),t([ut()],xt.prototype,"_saved",void 0),t([ut()],xt.prototype,"_testing",void 0),xt=t([ct("clicker-learn-drawer")],xt);const wt={fan:"mdi:fan",light:"mdi:lightbulb",switch:"mdi:toggle-switch-variant",button:"mdi:gesture-tap-button"};let At=class extends ot{constructor(){super(...arguments),this.radios=[],this._sending=new Set,this._learning=!1}_toast(t){this.dispatchEvent(new CustomEvent("hass-notification",{detail:{message:t},bubbles:!0,composed:!0}))}async _call(t,e){try{return await t(),e&&this._toast(e),!0}catch(t){return this._toast(mt(t)),!1}}_currentSettings(){return this._settings??{name:this.device.name,area:this.device.area_id??"",radio:this.device.radio_id}}_settingsChanged(){const t=this._currentSettings();return t.name.trim()!==this.device.name||t.area!==(this.device.area_id??"")||t.radio!==this.device.radio_id}async _saveSettings(){const t=this._currentSettings(),e={};t.name.trim()!==this.device.name&&(e.name=t.name.trim()),t.area!==(this.device.area_id??"")&&(e.area_id=t.area||null),t.radio!==this.device.radio_id&&(e.radio_id=t.radio),await this._call(()=>((t,e,i)=>t.connection.sendMessagePromise({type:"clicker/device/update",device_id:e,...i}))(this.hass,this.device.id,e),"Saved")&&(this._settings=void 0)}_renderSettings(){const t=this._currentSettings(),e=e=>this._settings={...t,...e},i=Object.values(this.hass.areas).sort((t,e)=>t.name.localeCompare(e.name)),s=function(t,e){return e.filter(e=>e.frequency_hz===t.frequency_hz).sort((e,i)=>e.id===t.radio_id?-1:i.id===t.radio_id?1:e.name.localeCompare(i.name))}(this.device,this.radios);return q`
      <div class="card">
        <div class="card-title">Device</div>
        <div class="settings">
          <label
            >Name
            <input
              .value=${t.name}
              @input=${t=>e({name:t.target.value})}
          /></label>
          <label
            >Area
            <select @change=${t=>e({area:t.target.value})}>
              <option value="" ?selected=${!t.area}>No area</option>
              ${i.map(e=>q`<option value=${e.area_id} ?selected=${e.area_id===t.area}>
                  ${e.name}
                </option>`)}
            </select></label
          >
          <label
            >Radio
            <select @change=${t=>e({radio:t.target.value})}>
              ${s.map(e=>q`<option value=${e.id} ?selected=${e.id===t.radio}>
                  ${gt(e.name,e.frequency_hz)}${e.online?"":" (offline)"}
                </option>`)}
            </select></label
          >
        </div>
        <div class="actions">
          ${this.device.ha_device_id?q`<a class="link" href="/config/devices/device/${this.device.ha_device_id}"
                >Open in Home Assistant</a
              >`:V}
          <span class="spacer"></span>
          ${this._settingsChanged()?q`<button @click=${()=>this._settings=void 0}>Cancel</button>
                <button class="primary" ?disabled=${!t.name.trim()} @click=${this._saveSettings}>
                  Save
                </button>`:V}
        </div>
      </div>
    `}async _test(t){this._sending=new Set([...this._sending,t.id]),await this._call(()=>{return e=this.hass,i=this.device.id,s=t.id,e.connection.sendMessagePromise({type:"clicker/command/send",device_id:i,command_id:s});var e,i,s},`Sent ${t.name}`),this._sending=new Set([...this._sending].filter(e=>e!==t.id))}async _saveCommand(){const t=this._editing,e=this.device.commands.find(e=>e.id===t.id);if(!e)return;const i={};t.name.trim()!==e.name&&(i.name=t.name.trim()),t.kind!==e.kind&&(i.kind=t.kind),t.frames!==e.frames_on_air&&(i.frames_on_air=t.frames),Object.keys(i).length?await this._call(()=>((t,e,i,s)=>t.connection.sendMessagePromise({type:"clicker/command/update",device_id:e,command_id:i,...s}))(this.hass,this.device.id,t.id,i),"Saved")&&(this._editing=void 0):this._editing=void 0}async _delete(t){await this._call(()=>{return e=this.hass,i=this.device.id,s=t.id,e.connection.sendMessagePromise({type:"clicker/command/delete",device_id:i,command_id:s});var e,i,s},`Deleted ${t.name}`)&&(this._confirmDelete=void 0)}_renderCommands(){const t=function(t){const e=new Map;for(const i of t.bindings)for(const[t,s]of Object.entries(i.roles)){const n=e.get(s)??[];n.push({bindingName:i.name,platform:i.platform,role:t}),e.set(s,n)}return e}(this.device);return q`
      <div class="card">
        <div class="card-title">
          Commands <span class="meta">${this.device.commands.length}</span>
          <span class="spacer"></span>
          ${this._learning?V:q`<button @click=${()=>this._learning=!0}>
                <ha-icon icon="mdi:plus"></ha-icon> Learn
              </button>`}
        </div>
        ${this.device.commands.length?this.device.commands.map(e=>this._renderCommand(e,t.get(e.id)??[])):q`<div class="meta">No commands yet. Press Learn, then press buttons on the remote.</div>`}
      </div>
    `}_renderCommand(t,e){if(this._editing?.id===t.id)return this._renderEditor(this._editing);const i=this._confirmDelete===t.id,s=this._sending.has(t.id);return q`
      <div class="row ${i?"confirming":""}">
        <div class="row-main">
          <div class="row-name">${t.name}</div>
          <div class="meta">
            ${ft[t.kind]} ·
            ${t.encoded?`${t.bits?.length??0}-bit ${t.encoding}`:"raw"} ·
            ${1===t.frames_on_air?"sent once":`${t.frames_on_air} frames`}
            ${e.length?q` · used by ${bt(e)}`:V}
          </div>
          ${i?q`<div class="confirm">
                ${e.length?q`Delete ${t.name}? ${bt(e)} will lose it, and an
                    entity that can't work without it is removed.`:q`Delete ${t.name}? You'd need to learn it again.`}
                <div class="actions">
                  <span class="spacer"></span>
                  <button @click=${()=>this._confirmDelete=void 0}>Cancel</button>
                  <button class="danger" @click=${()=>this._delete(t)}>Delete</button>
                </div>
              </div>`:V}
        </div>
        ${i?V:q`<button ?disabled=${s} @click=${()=>this._test(t)}>
                ${s?"Sending…":"Test"}
              </button>
              <button
                class="icon"
                aria-label="Edit ${t.name}"
                @click=${()=>this._editing={id:t.id,name:t.name,kind:t.kind,frames:t.frames_on_air}}
              >
                <ha-icon icon="mdi:pencil"></ha-icon>
              </button>
              <button
                class="icon"
                aria-label="Delete ${t.name}"
                @click=${()=>this._confirmDelete=t.id}
              >
                <ha-icon icon="mdi:delete-outline"></ha-icon>
              </button>`}
      </div>
    `}_renderEditor(t){const e=e=>this._editing={...t,...e},i=Number.isInteger(t.frames)&&t.frames>=1&&t.frames<=64;return q`
      <div class="row editing">
        <div class="editor">
          <label
            >Name
            <input
              .value=${t.name}
              @input=${t=>e({name:t.target.value})}
          /></label>
          <label
            >Kind
            <select @change=${t=>e({kind:t.target.value})}>
              ${Object.entries(ft).map(([e,i])=>q`<option value=${e} ?selected=${e===t.kind}>
                  ${i}
                </option>`)}
            </select>
            <span class="hint">${$t[t.kind]}</span></label
          >
          <label
            >Frames on air
            <input
              type="number"
              min="1"
              max="64"
              .value=${String(t.frames)}
              @input=${t=>e({frames:Number(t.target.value)})}
            />
            <span class="hint ${i?"":"error"}"
              >${i?"1 sends once; 8 is a short press":"Enter 1 to 64"}</span
            ></label
          >
        </div>
        <div class="actions">
          <span class="spacer"></span>
          <button @click=${()=>this._editing=void 0}>Cancel</button>
          <button class="primary" ?disabled=${!t.name.trim()||!i} @click=${this._saveCommand}>
            Save
          </button>
        </div>
      </div>
    `}_renderEntities(){const t=this.device.bindings.flatMap(t=>(t.entity_ids.length?t.entity_ids:[void 0]).map(e=>({b:t,entityId:e})));return q`
      <div class="card">
        <div class="card-title">Entities</div>
        ${t.length?t.map(({b:t,entityId:e})=>{const i=e?this.hass.states[e]:void 0;return q`<div class="entity">
                <ha-icon .icon=${wt[t.platform]??"mdi:remote"}></ha-icon>
                <div class="row-main">
                  <div>${i?.attributes.friendly_name??t.name}</div>
                  <div class="meta">${e??"Not created"}</div>
                </div>
                <span class="meta">${_t(i)}</span>
              </div>`}):q`<div class="meta">No entities yet.</div>`}
      </div>
    `}render(){return q`
      <div class="layout">
        <div class="column">${this._renderCommands()}</div>
        <div class="column">
          ${this._learning?q`<clicker-learn-drawer
                .hass=${this.hass}
                .device=${this.device}
                @close=${()=>this._learning=!1}
              ></clicker-learn-drawer>`:V}
          ${this._renderSettings()} ${this._renderEntities()}
        </div>
      </div>
    `}};At.styles=[yt,a`
      .layout {
        display: grid;
        grid-template-columns: minmax(0, 3fr) minmax(0, 2fr);
        gap: 12px;
        align-items: start;
      }
      @media (max-width: 800px) {
        .layout {
          grid-template-columns: minmax(0, 1fr);
        }
      }
      .card-title button {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        font-weight: 400;
      }
      .card-title button ha-icon {
        --mdc-icon-size: 18px;
      }
      .column {
        display: flex;
        flex-direction: column;
        gap: 12px;
      }
      .settings {
        display: flex;
        flex-direction: column;
        gap: 10px;
      }
      .actions {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-top: 10px;
      }
      .spacer {
        flex: 1;
      }
      .link {
        color: var(--primary-color);
        font-size: 14px;
        text-decoration: none;
      }
      .row {
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 8px 0;
        border-top: 1px solid var(--divider-color);
      }
      .row:first-of-type {
        border-top: none;
      }
      .row.editing {
        flex-direction: column;
        align-items: stretch;
      }
      .row-main {
        flex: 1;
        min-width: 0;
      }
      .row-name {
        font-size: 15px;
      }
      .confirm {
        margin-top: 6px;
        font-size: 14px;
      }
      .editor {
        display: grid;
        grid-template-columns: minmax(0, 2fr) minmax(0, 1fr) minmax(0, 1fr);
        gap: 10px;
      }
      @media (max-width: 500px) {
        .editor {
          grid-template-columns: minmax(0, 1fr);
        }
      }
      .hint {
        font-size: 12px;
        color: var(--secondary-text-color);
      }
      .hint.error {
        color: var(--error-color);
      }
      .entity {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 6px 0;
      }
      .entity ha-icon {
        color: var(--state-icon-color, var(--secondary-text-color));
      }
    `],t([pt({attribute:!1})],At.prototype,"hass",void 0),t([pt({attribute:!1})],At.prototype,"device",void 0),t([pt({attribute:!1})],At.prototype,"radios",void 0),t([ut()],At.prototype,"_editing",void 0),t([ut()],At.prototype,"_confirmDelete",void 0),t([ut()],At.prototype,"_sending",void 0),t([ut()],At.prototype,"_settings",void 0),t([ut()],At.prototype,"_learning",void 0),At=t([ct("clicker-device-page")],At);const kt={fan:"mdi:fan",light:"mdi:lightbulb",switch:"mdi:toggle-switch-variant",button:"mdi:gesture-tap-button"};let St=class extends ot{constructor(){super(...arguments),this.narrow=!1}updated(t){t.has("hass")&&this.hass&&!this._unsubscribe&&this._subscribe()}connectedCallback(){super.connectedCallback(),this.hass&&!this._unsubscribe&&this._subscribe()}disconnectedCallback(){super.disconnectedCallback(),this._unsubscribe?.then(t=>t()).catch(()=>{}),this._unsubscribe=void 0}_subscribe(){this._unsubscribe=this.hass.connection.subscribeMessage(t=>{this._data=t,this._error=void 0},{type:"clicker/data/subscribe"}),this._unsubscribe.catch(t=>{this._error=t.message??"Clicker isn't responding. Check that it's loaded.",this._unsubscribe=void 0})}_navigate(t){history.pushState(null,"",`${this.route?.prefix??"/clicker"}${t}`),window.dispatchEvent(new CustomEvent("location-changed",{detail:{replace:!1}}))}get _deviceId(){return/^\/device\/([^/]+)/.exec(this.route?.path??"")?.[1]}render(){const t=this._deviceId,e=t?this._data?.devices.find(e=>e.id===t):void 0;return t&&this._data&&this.hass?q`
        <div class="toolbar">
          <button class="back" aria-label="Back to devices" @click=${()=>this._navigate("")}>
            <ha-icon icon="mdi:arrow-left"></ha-icon>
          </button>
          <div class="title">${e?.name??"Device not found"}</div>
        </div>
        <div class="content">
          ${e?q`<clicker-device-page
                .hass=${this.hass}
                .device=${e}
                .radios=${this._data.radios}
              ></clicker-device-page>`:q`<p class="notice">This device was deleted.</p>`}
        </div>
      `:q`
      <div class="toolbar">
        <ha-menu-button .hass=${this.hass} .narrow=${this.narrow}></ha-menu-button>
        <div class="title">Clicker</div>
      </div>
      <div class="content">${this._renderBody()}</div>
    `}_renderBody(){if(this._error)return q`<p class="notice error">${this._error}</p>`;if(!this._data||!this.hass)return q`<p class="notice">Loading…</p>`;const{devices:t,radios:e,problems:i}=this._data;if(!t.length)return q`<div class="empty">
        <h2>Set up your first remote</h2>
        <p>Clicker learns your RF remotes' buttons and turns them into fans, lights, switches and buttons.</p>
        <p class="hint">${e.length?`Radios ready: ${e.map(t=>`${t.name}`).join(", ")}.`:"No radios yet. Clicker finds ESPHome radios with an RF transmitter or receiver."}</p>
      </div>`;const s=new Map(e.map(t=>[t.id,t]));return q`
      ${i.length?q`<div class="problems">${i.map(t=>q`<div>${t}</div>`)}</div>`:V}
      ${function(t,e,i="No area"){const s=new Map;for(const n of t){const t=n.area_id&&e[n.area_id]?n.area_id:null;let r=s.get(t);r||(r={areaId:t,name:t?e[t].name:i,devices:[]},s.set(t,r)),r.devices.push(n)}const n=(t,e)=>t.name.localeCompare(e.name,void 0,{sensitivity:"base"}),r=[...s.values()].sort((t,e)=>null===t.areaId?1:null===e.areaId?-1:n(t,e));for(const t of r)t.devices.sort(n);return r}(t,this.hass.areas).map(t=>q`
          <h2 class="area">${t.name}</h2>
          <div class="grid">
            ${t.devices.map(t=>this._renderDevice(t,s.get(t.radio_id)))}
          </div>
        `)}
    `}_renderDevice(t,e){const i=t.bindings.flatMap(t=>(t.entity_ids.length?t.entity_ids:[void 0]).map(e=>({binding:t,entityId:e})));return q`
      <div
        class="card clickable"
        role="button"
        tabindex="0"
        @click=${()=>this._navigate(`/device/${t.id}`)}
        @keydown=${e=>"Enter"===e.key&&this._navigate(`/device/${t.id}`)}
      >
        <div class="card-head">
          <span class="name">${t.name}</span>
          ${e?.online?V:q`<span class="badge warning">${e?"Radio offline":"No radio"}</span>`}
        </div>
        <div class="meta">
          ${gt(e?.name,t.frequency_hz)} ·
          ${function(t,e,i=`${e}s`){return`${t} ${1===t?e:i}`}(t.commands.length,"command")}
        </div>
        ${i.length?q`<div class="entities">
              ${i.map(({binding:t,entityId:e})=>{const i=e?this.hass.states[e]:void 0,s=i?.attributes.friendly_name??t.name;return q`<div class="entity">
                  <ha-icon .icon=${kt[t.platform]??"mdi:remote"}></ha-icon>
                  <span class="entity-name">${s}</span>
                  <span class="entity-state">${_t(i)}</span>
                </div>`})}
            </div>`:q`<div class="meta">No entities yet</div>`}
      </div>
    `}};St.styles=a`
    :host {
      display: block;
      min-height: 100vh;
      background: var(--primary-background-color);
      color: var(--primary-text-color);
      font-family: var(--ha-font-family-body, Roboto, sans-serif);
    }
    .toolbar {
      display: flex;
      align-items: center;
      height: var(--header-height, 56px);
      padding: 0 12px;
      background: var(--app-header-background-color);
      color: var(--app-header-text-color, white);
      border-bottom: var(--app-header-border-bottom, none);
      box-sizing: border-box;
    }
    .title {
      margin-left: 12px;
      font-size: 20px;
    }
    .back {
      display: inline-flex;
      background: none;
      border: none;
      color: inherit;
      padding: 8px;
      cursor: pointer;
    }
    .clickable {
      cursor: pointer;
    }
    .clickable:hover,
    .clickable:focus-visible {
      border-color: var(--primary-color);
      outline: none;
    }
    .content {
      max-width: 1040px;
      margin: 0 auto;
      padding: 8px 16px 32px;
    }
    .area {
      font-size: 16px;
      font-weight: 500;
      color: var(--secondary-text-color);
      margin: 20px 4px 8px;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 12px;
    }
    .card {
      background: var(--card-background-color);
      border-radius: var(--ha-card-border-radius, 12px);
      border: 1px solid var(--divider-color);
      padding: 14px 16px;
    }
    .card-head {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .name {
      font-size: 16px;
      font-weight: 500;
      flex: 1;
    }
    .meta {
      color: var(--secondary-text-color);
      font-size: 13px;
      margin-top: 4px;
    }
    .entities {
      margin-top: 10px;
      border-top: 1px solid var(--divider-color);
      padding-top: 8px;
    }
    .entity {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 4px 0;
      font-size: 14px;
    }
    .entity ha-icon {
      color: var(--state-icon-color, var(--secondary-text-color));
      --mdc-icon-size: 20px;
    }
    .entity-name {
      flex: 1;
    }
    .entity-state {
      color: var(--secondary-text-color);
      font-size: 13px;
    }
    .badge {
      font-size: 12px;
      padding: 2px 8px;
      border-radius: 10px;
    }
    .badge.warning {
      color: var(--warning-color);
      border: 1px solid var(--warning-color);
    }
    .problems {
      margin: 12px 0;
      padding: 10px 14px;
      border-radius: 8px;
      border: 1px solid var(--warning-color);
      font-size: 14px;
    }
    .notice {
      color: var(--secondary-text-color);
      padding: 24px 4px;
    }
    .notice.error {
      color: var(--error-color);
    }
    .empty {
      text-align: center;
      padding: 48px 16px;
    }
    .empty h2 {
      font-weight: 400;
    }
    .hint {
      color: var(--secondary-text-color);
      font-size: 14px;
    }
  `,t([pt({attribute:!1})],St.prototype,"hass",void 0),t([pt({type:Boolean})],St.prototype,"narrow",void 0),t([pt({attribute:!1})],St.prototype,"route",void 0),t([ut()],St.prototype,"_data",void 0),t([ut()],St.prototype,"_error",void 0),St=t([ct("clicker-panel")],St);export{St as ClickerPanel};
