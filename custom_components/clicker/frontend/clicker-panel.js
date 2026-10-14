function e(e,t,i,s){var n,o=arguments.length,r=o<3?t:null===s?s=Object.getOwnPropertyDescriptor(t,i):s;if("object"==typeof Reflect&&"function"==typeof Reflect.decorate)r=Reflect.decorate(e,t,i,s);else for(var a=e.length-1;a>=0;a--)(n=e[a])&&(r=(o<3?n(r):o>3?n(t,i,r):n(t,i))||r);return o>3&&r&&Object.defineProperty(t,i,r),r}"function"==typeof SuppressedError&&SuppressedError;const t=globalThis,i=t.ShadowRoot&&(void 0===t.ShadyCSS||t.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,s=Symbol(),n=new WeakMap;let o=class{constructor(e,t,i){if(this._$cssResult$=!0,i!==s)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=e,this.t=t}get styleSheet(){let e=this.o;const t=this.t;if(i&&void 0===e){const i=void 0!==t&&1===t.length;i&&(e=n.get(t)),void 0===e&&((this.o=e=new CSSStyleSheet).replaceSync(this.cssText),i&&n.set(t,e))}return e}toString(){return this.cssText}};const r=(e,...t)=>{const i=1===e.length?e[0]:t.reduce((t,i,s)=>t+(e=>{if(!0===e._$cssResult$)return e.cssText;if("number"==typeof e)return e;throw Error("Value passed to 'css' function must be a 'css' function result: "+e+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(i)+e[s+1],e[0]);return new o(i,e,s)},a=i?e=>e:e=>e instanceof CSSStyleSheet?(e=>{let t="";for(const i of e.cssRules)t+=i.cssText;return(e=>new o("string"==typeof e?e:e+"",void 0,s))(t)})(e):e,{is:d,defineProperty:c,getOwnPropertyDescriptor:l,getOwnPropertyNames:h,getOwnPropertySymbols:p,getPrototypeOf:m}=Object,u=globalThis,v=u.trustedTypes,g=v?v.emptyScript:"",_=u.reactiveElementPolyfillSupport,f=(e,t)=>e,b={toAttribute(e,t){switch(t){case Boolean:e=e?g:null;break;case Object:case Array:e=null==e?e:JSON.stringify(e)}return e},fromAttribute(e,t){let i=e;switch(t){case Boolean:i=null!==e;break;case Number:i=null===e?null:Number(e);break;case Object:case Array:try{i=JSON.parse(e)}catch(e){i=null}}return i}},$=(e,t)=>!d(e,t),y={attribute:!0,type:String,converter:b,reflect:!1,useDefault:!1,hasChanged:$};Symbol.metadata??=Symbol("metadata"),u.litPropertyMetadata??=new WeakMap;let x=class extends HTMLElement{static addInitializer(e){this._$Ei(),(this.l??=[]).push(e)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(e,t=y){if(t.state&&(t.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(e)&&((t=Object.create(t)).wrapped=!0),this.elementProperties.set(e,t),!t.noAccessor){const i=Symbol(),s=this.getPropertyDescriptor(e,i,t);void 0!==s&&c(this.prototype,e,s)}}static getPropertyDescriptor(e,t,i){const{get:s,set:n}=l(this.prototype,e)??{get(){return this[t]},set(e){this[t]=e}};return{get:s,set(t){const o=s?.call(this);n?.call(this,t),this.requestUpdate(e,o,i)},configurable:!0,enumerable:!0}}static getPropertyOptions(e){return this.elementProperties.get(e)??y}static _$Ei(){if(this.hasOwnProperty(f("elementProperties")))return;const e=m(this);e.finalize(),void 0!==e.l&&(this.l=[...e.l]),this.elementProperties=new Map(e.elementProperties)}static finalize(){if(this.hasOwnProperty(f("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(f("properties"))){const e=this.properties,t=[...h(e),...p(e)];for(const i of t)this.createProperty(i,e[i])}const e=this[Symbol.metadata];if(null!==e){const t=litPropertyMetadata.get(e);if(void 0!==t)for(const[e,i]of t)this.elementProperties.set(e,i)}this._$Eh=new Map;for(const[e,t]of this.elementProperties){const i=this._$Eu(e,t);void 0!==i&&this._$Eh.set(i,e)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(e){const t=[];if(Array.isArray(e)){const i=new Set(e.flat(1/0).reverse());for(const e of i)t.unshift(a(e))}else void 0!==e&&t.push(a(e));return t}static _$Eu(e,t){const i=t.attribute;return!1===i?void 0:"string"==typeof i?i:"string"==typeof e?e.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(e=>this.enableUpdating=e),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(e=>e(this))}addController(e){(this._$EO??=new Set).add(e),void 0!==this.renderRoot&&this.isConnected&&e.hostConnected?.()}removeController(e){this._$EO?.delete(e)}_$E_(){const e=new Map,t=this.constructor.elementProperties;for(const i of t.keys())this.hasOwnProperty(i)&&(e.set(i,this[i]),delete this[i]);e.size>0&&(this._$Ep=e)}createRenderRoot(){const e=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return((e,s)=>{if(i)e.adoptedStyleSheets=s.map(e=>e instanceof CSSStyleSheet?e:e.styleSheet);else for(const i of s){const s=document.createElement("style"),n=t.litNonce;void 0!==n&&s.setAttribute("nonce",n),s.textContent=i.cssText,e.appendChild(s)}})(e,this.constructor.elementStyles),e}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(e=>e.hostConnected?.())}enableUpdating(e){}disconnectedCallback(){this._$EO?.forEach(e=>e.hostDisconnected?.())}attributeChangedCallback(e,t,i){this._$AK(e,i)}_$ET(e,t){const i=this.constructor.elementProperties.get(e),s=this.constructor._$Eu(e,i);if(void 0!==s&&!0===i.reflect){const n=(void 0!==i.converter?.toAttribute?i.converter:b).toAttribute(t,i.type);this._$Em=e,null==n?this.removeAttribute(s):this.setAttribute(s,n),this._$Em=null}}_$AK(e,t){const i=this.constructor,s=i._$Eh.get(e);if(void 0!==s&&this._$Em!==s){const e=i.getPropertyOptions(s),n="function"==typeof e.converter?{fromAttribute:e.converter}:void 0!==e.converter?.fromAttribute?e.converter:b;this._$Em=s;const o=n.fromAttribute(t,e.type);this[s]=o??this._$Ej?.get(s)??o,this._$Em=null}}requestUpdate(e,t,i,s=!1,n){if(void 0!==e){const o=this.constructor;if(!1===s&&(n=this[e]),i??=o.getPropertyOptions(e),!((i.hasChanged??$)(n,t)||i.useDefault&&i.reflect&&n===this._$Ej?.get(e)&&!this.hasAttribute(o._$Eu(e,i))))return;this.C(e,t,i)}!1===this.isUpdatePending&&(this._$ES=this._$EP())}C(e,t,{useDefault:i,reflect:s,wrapped:n},o){i&&!(this._$Ej??=new Map).has(e)&&(this._$Ej.set(e,o??t??this[e]),!0!==n||void 0!==o)||(this._$AL.has(e)||(this.hasUpdated||i||(t=void 0),this._$AL.set(e,t)),!0===s&&this._$Em!==e&&(this._$Eq??=new Set).add(e))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(e){Promise.reject(e)}const e=this.scheduleUpdate();return null!=e&&await e,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(const[e,t]of this._$Ep)this[e]=t;this._$Ep=void 0}const e=this.constructor.elementProperties;if(e.size>0)for(const[t,i]of e){const{wrapped:e}=i,s=this[t];!0!==e||this._$AL.has(t)||void 0===s||this.C(t,void 0,i,s)}}let e=!1;const t=this._$AL;try{e=this.shouldUpdate(t),e?(this.willUpdate(t),this._$EO?.forEach(e=>e.hostUpdate?.()),this.update(t)):this._$EM()}catch(t){throw e=!1,this._$EM(),t}e&&this._$AE(t)}willUpdate(e){}_$AE(e){this._$EO?.forEach(e=>e.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(e)),this.updated(e)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(e){return!0}update(e){this._$Eq&&=this._$Eq.forEach(e=>this._$ET(e,this[e])),this._$EM()}updated(e){}firstUpdated(e){}};x.elementStyles=[],x.shadowRootOptions={mode:"open"},x[f("elementProperties")]=new Map,x[f("finalized")]=new Map,_?.({ReactiveElement:x}),(u.reactiveElementVersions??=[]).push("2.1.2");const w=globalThis,k=e=>e,A=w.trustedTypes,S=A?A.createPolicy("lit-html",{createHTML:e=>e}):void 0,E="$lit$",C=`lit$${Math.random().toFixed(9).slice(2)}$`,O="?"+C,P=`<${O}>`,R=document,z=()=>R.createComment(""),M=e=>null===e||"object"!=typeof e&&"function"!=typeof e,N=Array.isArray,T="[ \t\n\f\r]",U=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,j=/-->/g,H=/>/g,B=RegExp(`>|${T}(?:([^\\s"'>=/]+)(${T}*=${T}*(?:[^ \t\n\f\r"'\`<>=]|("|')|))|$)`,"g"),D=/'/g,L=/"/g,q=/^(?:script|style|textarea|title)$/i,I=(e=>(t,...i)=>({_$litType$:e,strings:t,values:i}))(1),F=Symbol.for("lit-noChange"),W=Symbol.for("lit-nothing"),V=new WeakMap,K=R.createTreeWalker(R,129);function J(e,t){if(!N(e)||!e.hasOwnProperty("raw"))throw Error("invalid template strings array");return void 0!==S?S.createHTML(t):t}const Z=(e,t)=>{const i=e.length-1,s=[];let n,o=2===t?"<svg>":3===t?"<math>":"",r=U;for(let t=0;t<i;t++){const i=e[t];let a,d,c=-1,l=0;for(;l<i.length&&(r.lastIndex=l,d=r.exec(i),null!==d);)l=r.lastIndex,r===U?"!--"===d[1]?r=j:void 0!==d[1]?r=H:void 0!==d[2]?(q.test(d[2])&&(n=RegExp("</"+d[2],"g")),r=B):void 0!==d[3]&&(r=B):r===B?">"===d[0]?(r=n??U,c=-1):void 0===d[1]?c=-2:(c=r.lastIndex-d[2].length,a=d[1],r=void 0===d[3]?B:'"'===d[3]?L:D):r===L||r===D?r=B:r===j||r===H?r=U:(r=B,n=void 0);const h=r===B&&e[t+1].startsWith("/>")?" ":"";o+=r===U?i+P:c>=0?(s.push(a),i.slice(0,c)+E+i.slice(c)+C+h):i+C+(-2===c?t:h)}return[J(e,o+(e[i]||"<?>")+(2===t?"</svg>":3===t?"</math>":"")),s]};class Y{constructor({strings:e,_$litType$:t},i){let s;this.parts=[];let n=0,o=0;const r=e.length-1,a=this.parts,[d,c]=Z(e,t);if(this.el=Y.createElement(d,i),K.currentNode=this.el.content,2===t||3===t){const e=this.el.content.firstChild;e.replaceWith(...e.childNodes)}for(;null!==(s=K.nextNode())&&a.length<r;){if(1===s.nodeType){if(s.hasAttributes())for(const e of s.getAttributeNames())if(e.endsWith(E)){const t=c[o++],i=s.getAttribute(e).split(C),r=/([.?@])?(.*)/.exec(t);a.push({type:1,index:n,name:r[2],strings:i,ctor:"."===r[1]?te:"?"===r[1]?ie:"@"===r[1]?se:ee}),s.removeAttribute(e)}else e.startsWith(C)&&(a.push({type:6,index:n}),s.removeAttribute(e));if(q.test(s.tagName)){const e=s.textContent.split(C),t=e.length-1;if(t>0){s.textContent=A?A.emptyScript:"";for(let i=0;i<t;i++)s.append(e[i],z()),K.nextNode(),a.push({type:2,index:++n});s.append(e[t],z())}}}else if(8===s.nodeType)if(s.data===O)a.push({type:2,index:n});else{let e=-1;for(;-1!==(e=s.data.indexOf(C,e+1));)a.push({type:7,index:n}),e+=C.length-1}n++}}static createElement(e,t){const i=R.createElement("template");return i.innerHTML=e,i}}function G(e,t,i=e,s){if(t===F)return t;let n=void 0!==s?i._$Co?.[s]:i._$Cl;const o=M(t)?void 0:t._$litDirective$;return n?.constructor!==o&&(n?._$AO?.(!1),void 0===o?n=void 0:(n=new o(e),n._$AT(e,i,s)),void 0!==s?(i._$Co??=[])[s]=n:i._$Cl=n),void 0!==n&&(t=G(e,n._$AS(e,t.values),n,s)),t}class Q{constructor(e,t){this._$AV=[],this._$AN=void 0,this._$AD=e,this._$AM=t}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(e){const{el:{content:t},parts:i}=this._$AD,s=(e?.creationScope??R).importNode(t,!0);K.currentNode=s;let n=K.nextNode(),o=0,r=0,a=i[0];for(;void 0!==a;){if(o===a.index){let t;2===a.type?t=new X(n,n.nextSibling,this,e):1===a.type?t=new a.ctor(n,a.name,a.strings,this,e):6===a.type&&(t=new ne(n,this,e)),this._$AV.push(t),a=i[++r]}o!==a?.index&&(n=K.nextNode(),o++)}return K.currentNode=R,s}p(e){let t=0;for(const i of this._$AV)void 0!==i&&(void 0!==i.strings?(i._$AI(e,i,t),t+=i.strings.length-2):i._$AI(e[t])),t++}}class X{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(e,t,i,s){this.type=2,this._$AH=W,this._$AN=void 0,this._$AA=e,this._$AB=t,this._$AM=i,this.options=s,this._$Cv=s?.isConnected??!0}get parentNode(){let e=this._$AA.parentNode;const t=this._$AM;return void 0!==t&&11===e?.nodeType&&(e=t.parentNode),e}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(e,t=this){e=G(this,e,t),M(e)?e===W||null==e||""===e?(this._$AH!==W&&this._$AR(),this._$AH=W):e!==this._$AH&&e!==F&&this._(e):void 0!==e._$litType$?this.$(e):void 0!==e.nodeType?this.T(e):(e=>N(e)||"function"==typeof e?.[Symbol.iterator])(e)?this.k(e):this._(e)}O(e){return this._$AA.parentNode.insertBefore(e,this._$AB)}T(e){this._$AH!==e&&(this._$AR(),this._$AH=this.O(e))}_(e){this._$AH!==W&&M(this._$AH)?this._$AA.nextSibling.data=e:this.T(R.createTextNode(e)),this._$AH=e}$(e){const{values:t,_$litType$:i}=e,s="number"==typeof i?this._$AC(e):(void 0===i.el&&(i.el=Y.createElement(J(i.h,i.h[0]),this.options)),i);if(this._$AH?._$AD===s)this._$AH.p(t);else{const e=new Q(s,this),i=e.u(this.options);e.p(t),this.T(i),this._$AH=e}}_$AC(e){let t=V.get(e.strings);return void 0===t&&V.set(e.strings,t=new Y(e)),t}k(e){N(this._$AH)||(this._$AH=[],this._$AR());const t=this._$AH;let i,s=0;for(const n of e)s===t.length?t.push(i=new X(this.O(z()),this.O(z()),this,this.options)):i=t[s],i._$AI(n),s++;s<t.length&&(this._$AR(i&&i._$AB.nextSibling,s),t.length=s)}_$AR(e=this._$AA.nextSibling,t){for(this._$AP?.(!1,!0,t);e!==this._$AB;){const t=k(e).nextSibling;k(e).remove(),e=t}}setConnected(e){void 0===this._$AM&&(this._$Cv=e,this._$AP?.(e))}}class ee{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(e,t,i,s,n){this.type=1,this._$AH=W,this._$AN=void 0,this.element=e,this.name=t,this._$AM=s,this.options=n,i.length>2||""!==i[0]||""!==i[1]?(this._$AH=Array(i.length-1).fill(new String),this.strings=i):this._$AH=W}_$AI(e,t=this,i,s){const n=this.strings;let o=!1;if(void 0===n)e=G(this,e,t,0),o=!M(e)||e!==this._$AH&&e!==F,o&&(this._$AH=e);else{const s=e;let r,a;for(e=n[0],r=0;r<n.length-1;r++)a=G(this,s[i+r],t,r),a===F&&(a=this._$AH[r]),o||=!M(a)||a!==this._$AH[r],a===W?e=W:e!==W&&(e+=(a??"")+n[r+1]),this._$AH[r]=a}o&&!s&&this.j(e)}j(e){e===W?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,e??"")}}class te extends ee{constructor(){super(...arguments),this.type=3}j(e){this.element[this.name]=e===W?void 0:e}}class ie extends ee{constructor(){super(...arguments),this.type=4}j(e){this.element.toggleAttribute(this.name,!!e&&e!==W)}}class se extends ee{constructor(e,t,i,s,n){super(e,t,i,s,n),this.type=5}_$AI(e,t=this){if((e=G(this,e,t,0)??W)===F)return;const i=this._$AH,s=e===W&&i!==W||e.capture!==i.capture||e.once!==i.once||e.passive!==i.passive,n=e!==W&&(i===W||s);s&&this.element.removeEventListener(this.name,this,i),n&&this.element.addEventListener(this.name,this,e),this._$AH=e}handleEvent(e){"function"==typeof this._$AH?this._$AH.call(this.options?.host??this.element,e):this._$AH.handleEvent(e)}}class ne{constructor(e,t,i){this.element=e,this.type=6,this._$AN=void 0,this._$AM=t,this.options=i}get _$AU(){return this._$AM._$AU}_$AI(e){G(this,e)}}const oe=w.litHtmlPolyfillSupport;oe?.(Y,X),(w.litHtmlVersions??=[]).push("3.3.3");const re=globalThis;class ae extends x{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){const e=super.createRenderRoot();return this.renderOptions.renderBefore??=e.firstChild,e}update(e){const t=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(e),this._$Do=((e,t,i)=>{const s=i?.renderBefore??t;let n=s._$litPart$;if(void 0===n){const e=i?.renderBefore??null;s._$litPart$=n=new X(t.insertBefore(z(),e),e,void 0,i??{})}return n._$AI(e),n})(t,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return F}}ae._$litElement$=!0,ae.finalized=!0,re.litElementHydrateSupport?.({LitElement:ae});const de=re.litElementPolyfillSupport;de?.({LitElement:ae}),(re.litElementVersions??=[]).push("4.2.2");const ce=e=>(t,i)=>{void 0!==i?i.addInitializer(()=>{customElements.define(e,t)}):customElements.define(e,t)},le={attribute:!0,type:String,converter:b,reflect:!1,hasChanged:$},he=(e=le,t,i)=>{const{kind:s,metadata:n}=i;let o=globalThis.litPropertyMetadata.get(n);if(void 0===o&&globalThis.litPropertyMetadata.set(n,o=new Map),"setter"===s&&((e=Object.create(e)).wrapped=!0),o.set(i.name,e),"accessor"===s){const{name:s}=i;return{set(i){const n=t.get.call(this);t.set.call(this,i),this.requestUpdate(s,n,e,!0,i)},init(t){return void 0!==t&&this.C(s,void 0,e,t),t}}}if("setter"===s){const{name:s}=i;return function(i){const n=this[s];t.call(this,i),this.requestUpdate(s,n,e,!0,i)}}throw Error("Unsupported decorator location: "+s)};function pe(e){return(t,i)=>"object"==typeof i?he(e,t,i):((e,t,i)=>{const s=t.hasOwnProperty(i);return t.constructor.createProperty(i,e),s?Object.getOwnPropertyDescriptor(t,i):void 0})(e,t,i)}function me(e){return pe({...e,state:!0,attribute:!1})}function ue(e){const t=e?.message;return"string"==typeof t&&t?t:"Something went wrong. Try again."}const ve=r`
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
`,ge={role:"oscillate",label:"Oscillate (toggle)",required:!1},_e={role:"direction",label:"Reverse (toggle)",required:!1},fe=[{id:"fan_toggle",platform:"fan",label:"Fan with a power toggle",hasSpeeds:!0,slots:[{role:"power",label:"Power (toggle)",required:!0},ge,_e]},{id:"fan_off",platform:"fan",label:"Fan with an Off button",hasSpeeds:!0,slots:[{role:"off",label:"Off",required:!0},{role:"on",label:"On",required:!1},ge,_e]},{id:"light_toggle",platform:"light",label:"Light with one toggle button",slots:[{role:"toggle",label:"Toggle",required:!0}]},{id:"light_onoff",platform:"light",label:"Light with On and Off buttons",slots:[{role:"on",label:"On",required:!0},{role:"off",label:"Off",required:!0}]},{id:"switch_toggle",platform:"switch",label:"Switch with one toggle button",slots:[{role:"toggle",label:"Toggle",required:!0}]},{id:"switch_onoff",platform:"switch",label:"Switch with On and Off buttons",slots:[{role:"on",label:"On",required:!0},{role:"off",label:"Off",required:!0}]},{id:"buttons",platform:"button",label:"Buttons",pickCommands:!0,slots:[]}],be=e=>fe.find(t=>t.id===e);function $e(e,t){const i=e.hasSpeeds?Array.from({length:t},(e,t)=>({role:`speed_${t+1}`,label:`Speed ${t+1}`,required:!0})):[],s=e.slots.filter(e=>e.required||"on"===e.role),n=e.slots.filter(e=>!s.includes(e));return[...s,...i,...n]}const ye={power:/power|on\s*\/\s*off/i,off:/^(fan\s+)?off$/i,on:/^(fan\s+)?on$/i,toggle:/light|lamp|toggle|power/i,oscillate:/oscillat|swing/i,direction:/reverse|direction/i};function xe(e,t){const i={},s=new Set;for(const n of e){const e=/^speed_(\d+)$/.exec(n.role)?.[1],o=e?new RegExp(`^(speed\\s*)?${e}$`,"i"):ye[n.role],r=o&&t.find(e=>!s.has(e.id)&&o.test(e.name.trim()));r&&(i[n.role]=r.id,s.add(r.id))}return i}function we(e){const t=Object.keys(e.roles),i=t.filter(e=>/^speed_\d+$/.test(e)).length,s="fan"===e.platform?t.includes("power")?"fan_toggle":"fan_off":"button"===e.platform?"buttons":`${e.platform}_${t.includes("on")&&t.includes("off")?"onoff":"toggle"}`;return{template:be(s),speeds:i}}const ke={fan:"Fan",light:"Light",switch:"Switch",button:"Buttons"};let Ae=class extends ae{constructor(){super(...arguments),this._name="",this._speeds=0,this._roles={},this._saving=!1}connectedCallback(){if(super.connectedCallback(),this.binding){const{template:e,speeds:t}=we(this.binding);this._template=e,this._speeds=t,this._name=this.binding.name,this._roles={...this.binding.roles}}else this._choose(fe[0]);this._scheduleCheck()}_defaultName(e){if("button"===e.platform)return ke.button;const t=this.device.bindings.some(t=>t.platform===e.platform);return t?ke[e.platform]:this.device.name}_choose(e){this._template=e,this.binding||(this._name=this._defaultName(e)),this._speeds=e.hasSpeeds?function(e){let t=0;for(;e.some(e=>new RegExp(`^(speed\\s*)?${t+1}$`,"i").test(e.name.trim()));)t++;return t}(this.device.commands):0,this._roles=e.pickCommands?{}:xe($e(e,this._speeds),this.device.commands),this._scheduleCheck()}_setSpeeds(e){this._speeds=Math.max(0,Math.min(10,e||0));const t=Object.fromEntries(Object.entries(this._roles).filter(([e])=>{const t=/^speed_(\d+)$/.exec(e)?.[1];return!t||Number(t)<=this._speeds})),i=xe($e(this._template,this._speeds),this.device.commands);for(const[e,s]of Object.entries(i))e in t||(t[e]=s);this._roles=t,this._scheduleCheck()}_setRole(e,t){const i={...this._roles};t?i[e]=t:delete i[e],this._roles=i,this._scheduleCheck()}_toggleButton(e,t,i){const s=Object.fromEntries(Object.entries(this._roles).filter(([,t])=>t!==e));i&&(s[function(e,t){const i=e.toLowerCase().replace(/[^a-z0-9]+/g,"_").replace(/^_|_$/g,"")||"button";let s=i;for(let e=2;t.has(s);e++)s=`${i}_${e}`;return s}(t,new Set(Object.keys(s)))]=e),this._roles=s,this._scheduleCheck()}_scheduleCheck(){window.clearTimeout(this._checkTimer),this._check=void 0,this._checkTimer=window.setTimeout(async()=>{try{this._check=await(e=this.hass,t=this.device.id,i=this._template.platform,s=this._roles,e.connection.sendMessagePromise({type:"clicker/binding/validate",device_id:t,platform:i,roles:s}))}catch(e){this._check={ok:!1,error:ue(e)}}var e,t,i,s},250)}_close(){this.dispatchEvent(new CustomEvent("close"))}async _save(){this._saving=!0;try{this.binding?await(e=this.hass,t=this.device.id,i=this.binding.id,s={name:this._name.trim(),roles:this._roles},e.connection.sendMessagePromise({type:"clicker/binding/update",device_id:t,binding_id:i,...s})):await((e,t,i)=>e.connection.sendMessagePromise({type:"clicker/binding/create",device_id:t,...i}))(this.hass,this.device.id,{platform:this._template.platform,name:this._name.trim(),roles:this._roles}),this.dispatchEvent(new CustomEvent("hass-notification",{detail:{message:this.binding?"Saved":`Added ${this._name.trim()}`},bubbles:!0,composed:!0})),this._close()}catch(e){this._check={ok:!1,error:ue(e)}}var e,t,i,s;this._saving=!1}render(){const e=this.binding?fe.filter(e=>e.platform===this.binding.platform):fe;return I`
      <div class="editor">
        <label
          >Type
          <select
            @change=${e=>this._choose(be(e.target.value))}
          >
            ${e.map(e=>I`<option value=${e.id} ?selected=${e.id===this._template.id}>${e.label}</option>`)}
          </select></label
        >
        <label
          >Name
          <input
            .value=${this._name}
            @input=${e=>this._name=e.target.value}
          />
          <span class="hint">
            ${this._name.trim().toLowerCase()===this.device.name.toLowerCase()?"Shown as just the device name":`Shown as ${this.device.name} ${this._name.trim()}`}
          </span></label
        >
        ${this._template.hasSpeeds?I`<label
              >Speeds
              <input
                type="number"
                min="0"
                max="10"
                .value=${String(this._speeds)}
                @input=${e=>this._setSpeeds(Number(e.target.value))}
            /></label>`:W}
        ${this._template.pickCommands?this._renderButtons():this._renderSlots()}
        <div class="status ${this._check?.ok?"ok":this._check?"error":""}">
          ${this._check?this._check.ok?"Ready to save":(t=this._check.error??"",t.charAt(0).toUpperCase()+t.slice(1)):"Checking…"}
        </div>
        <div class="actions">
          <span class="spacer"></span>
          <button @click=${this._close}>Cancel</button>
          <button
            class="primary"
            ?disabled=${!this._check?.ok||!this._name.trim()||this._saving}
            @click=${this._save}
          >
            ${this.binding?"Save":"Add"}
          </button>
        </div>
      </div>
    `;var t}_renderSlots(){return I`<div class="slots">
      ${$e(this._template,this._speeds).map(e=>I`<label class="slot"
          ><span>${e.label}${e.required?"":I` <span class="optional">optional</span>`}</span>
          <select @change=${t=>this._setRole(e.role,t.target.value)}>
            <option value="" ?selected=${!this._roles[e.role]}>${e.required?"Choose…":"None"}</option>
            ${this.device.commands.map(t=>I`<option value=${t.id} ?selected=${this._roles[e.role]===t.id}>${t.name}</option>`)}
          </select></label
        >`)}
    </div>`}_renderButtons(){const e=new Set(Object.values(this._roles));return I`<div class="buttons">
      <span class="hint">Each command you pick becomes its own button entity.</span>
      ${this.device.commands.map(t=>I`<label class="check"
          ><input
            type="checkbox"
            .checked=${e.has(t.id)}
            @change=${e=>this._toggleButton(t.id,t.name,e.target.checked)}
          />${t.name}</label
        >`)}
    </div>`}};function Se(e){return`${(e/1e6).toFixed(2)} MHz`}function Ee(e,t){const i=Se(t);return e?e.includes(i)?e:`${e} · ${i}`:i}function Ce(e){if(!e)return"Not created";switch(e.state){case"unavailable":return"Unavailable";case"on":{const t=e.attributes.percentage;return"number"==typeof t?`On, ${t}%`:"On"}case"off":return"Off";default:return e.entity_id.startsWith("button.")?"":e.state}}Ae.styles=[ve,r`
      .editor {
        display: flex;
        flex-direction: column;
        gap: 10px;
        padding: 10px 0;
      }
      .slots {
        display: flex;
        flex-direction: column;
        gap: 6px;
      }
      label.slot {
        flex-direction: row;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
        color: var(--primary-text-color);
        font-size: 14px;
      }
      label.slot select {
        min-width: 50%;
      }
      .optional {
        color: var(--secondary-text-color);
        font-size: 12px;
      }
      .buttons {
        display: flex;
        flex-direction: column;
        gap: 4px;
      }
      label.check {
        flex-direction: row;
        align-items: center;
        gap: 8px;
        color: var(--primary-text-color);
        font-size: 14px;
      }
      .hint {
        font-size: 12px;
        color: var(--secondary-text-color);
      }
      .status {
        font-size: 13px;
        color: var(--secondary-text-color);
      }
      .status.ok {
        color: var(--success-color);
      }
      .status.error {
        color: var(--error-color);
      }
      .actions {
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .spacer {
        flex: 1;
      }
    `],e([pe({attribute:!1})],Ae.prototype,"hass",void 0),e([pe({attribute:!1})],Ae.prototype,"device",void 0),e([pe({attribute:!1})],Ae.prototype,"binding",void 0),e([me()],Ae.prototype,"_template",void 0),e([me()],Ae.prototype,"_name",void 0),e([me()],Ae.prototype,"_speeds",void 0),e([me()],Ae.prototype,"_roles",void 0),e([me()],Ae.prototype,"_check",void 0),e([me()],Ae.prototype,"_saving",void 0),Ae=e([ce("clicker-entity-editor")],Ae);const Oe={button:"Button",toggle:"Toggle",state:"State"},Pe={button:"Always sent; no state",toggle:"Flips the state; sent only to change it",state:"Sets one state; safe to resend"};function Re(e){const t=new Set,i=[];for(const s of e){const e=`${s.bindingName} (${s.platform})`;t.has(e)||(t.add(e),i.push(e))}return i.join(", ")}let ze=class extends ae{constructor(){super(...arguments),this._saved=new Map}connectedCallback(){super.connectedCallback(),this._unsubscribe=this.hass.connection.subscribeMessage(e=>{this._update=e},{type:"clicker/learn/subscribe",device_id:this.device.id}),this._unsubscribe.catch(e=>this._error=ue(e))}disconnectedCallback(){super.disconnectedCallback(),this._unsubscribe?.then(e=>e()).catch(()=>{}),this._unsubscribe=void 0}_toast(e){this.dispatchEvent(new CustomEvent("hass-notification",{detail:{message:e},bubbles:!0,composed:!0}))}_close(){this.dispatchEvent(new CustomEvent("close"))}async _test(e){if(this._update){this._testing=e.fingerprint;try{await(t=this.hass,i=this._update.session_id,s=e.fingerprint,t.connection.sendMessagePromise({type:"clicker/learn/test",session_id:i,fingerprint:s})),this._toast("Sent. Did the device respond?")}catch(e){this._toast(ue(e))}var t,i,s;this._testing=void 0}}_startSave(e){this._draft={fingerprint:e.fingerprint,mode:"new",name:"",kind:"button",commandId:this.device.commands[0]?.id??""}}_nameTaken(e){return this.device.commands.some(t=>t.name.toLowerCase()===e.trim().toLowerCase())}async _save(){const e=this._draft;if(!e||!this._update)return;const t="new"===e.mode?{name:e.name.trim(),kind:e.kind}:{command_id:e.commandId};try{const i=await((e,t,i,s)=>e.connection.sendMessagePromise({type:"clicker/learn/save",session_id:t,fingerprint:i,...s}))(this.hass,this._update.session_id,e.fingerprint,t);this._saved=new Map([...this._saved,[e.fingerprint,i.name]]),this._draft=void 0,this._toast("new"===e.mode?`Saved ${i.name}`:`Relearned ${i.name}`)}catch(e){this._toast(ue(e))}}render(){const e=this._update?Se(this._update.frequency_hz):Se(this.device.frequency_hz),t=this._update?.candidates??[];return I`
      <div class="card learning">
        <div class="card-title">
          Learn <span class="spacer"></span>
          <button class="icon" aria-label="Stop learning" @click=${this._close}>
            <ha-icon icon="mdi:close"></ha-icon>
          </button>
        </div>
        ${this._error?I`<div class="error">${this._error}</div>`:I`<div class="listening">
              <span class="dot"></span>
              ${this._update?`Listening on ${e}. Press a button on the remote 2 or 3 times.`:"Starting…"}
            </div>`}
        ${t.map(e=>this._renderCandidate(e))}
      </div>
    `}_renderCandidate(e){const t=this._saved.get(e.fingerprint),i=e.known_as.find(e=>e.device===this.device.name),s=e.known_as.filter(e=>e.device!==this.device.name),n=this._draft?.fingerprint===e.fingerprint;return I`
      <div class="candidate">
        <div class="candidate-head">
          <span class="candidate-title">${function(e){if(!e.bits)return"Raw code";const t=e.bits.slice(-8);return`${e.bits.length}-bit code ${e.bits.length>8?"…":""}${t}`}(e)}</span>
          ${t?I`<span class="chip success">Saved as ${t}</span>`:i?I`<span class="chip warning">Already ${i.command}</span>`:I`<span class="chip">New</span>`}
        </div>
        <div class="meta">${function(e){const t=[e.usable?e.encoded?"Encoded":"Raw replay":"Too short to use",`seen ${e.sightings}×`];return e.variants>1&&t.push(`${e.variants} variants`),t.join(" · ")}(e)}</div>
        ${s.length?I`<div class="meta">
              Also sent by ${s.map(e=>`${e.device} / ${e.command}`).join(", ")}
            </div>`:W}
        ${n?this._renderDraft(this._draft):e.usable?I`<div class="actions">
                <button
                  ?disabled=${this._testing===e.fingerprint}
                  @click=${()=>this._test(e)}
                >
                  ${this._testing===e.fingerprint?"Sending…":"Test"}
                </button>
                ${t?W:I`<button @click=${()=>this._startSave(e)}>Save…</button>`}
              </div>`:W}
      </div>
    `}_renderDraft(e){const t=t=>this._draft={...e,...t},i="new"===e.mode&&this._nameTaken(e.name),s="new"===e.mode?!!e.name.trim()&&!i:!!e.commandId;return I`
      <div class="draft">
        <div class="modes">
          <label class="radio"
            ><input
              type="radio"
              name="mode"
              .checked=${"new"===e.mode}
              @change=${()=>t({mode:"new"})}
            />New command</label
          >
          ${this.device.commands.length?I`<label class="radio"
                ><input
                  type="radio"
                  name="mode"
                  .checked=${"replace"===e.mode}
                  @change=${()=>t({mode:"replace"})}
                />Relearn an existing one</label
              >`:W}
        </div>
        ${"new"===e.mode?I`<label
                >Name
                <input
                  placeholder="Light"
                  .value=${e.name}
                  @input=${e=>t({name:e.target.value})}
                />
                ${i?I`<span class="hint error">${this.device.name} already has one</span>`:W}
              </label>
              <label
                >Kind
                <select @change=${e=>t({kind:e.target.value})}>
                  ${Object.entries(Oe).map(([t,i])=>I`<option value=${t} ?selected=${t===e.kind}>
                      ${i}
                    </option>`)}
                </select>
                <span class="hint">${Pe[e.kind]}</span>
              </label>`:I`<label
              >Replace the code of
              <select @change=${e=>t({commandId:e.target.value})}>
                ${this.device.commands.map(t=>I`<option value=${t.id} ?selected=${t.id===e.commandId}>${t.name}</option>`)}
              </select>
            </label>`}
        <div class="actions">
          <span class="spacer"></span>
          <button @click=${()=>this._draft=void 0}>Cancel</button>
          <button class="primary" ?disabled=${!s} @click=${this._save}>
            ${"new"===e.mode?"Save":"Relearn"}
          </button>
        </div>
      </div>
    `}};ze.styles=[ve,r`
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
    `],e([pe({attribute:!1})],ze.prototype,"hass",void 0),e([pe({attribute:!1})],ze.prototype,"device",void 0),e([me()],ze.prototype,"_update",void 0),e([me()],ze.prototype,"_error",void 0),e([me()],ze.prototype,"_draft",void 0),e([me()],ze.prototype,"_saved",void 0),e([me()],ze.prototype,"_testing",void 0),ze=e([ce("clicker-learn-drawer")],ze);const Me={fan:"mdi:fan",light:"mdi:lightbulb",switch:"mdi:toggle-switch-variant",button:"mdi:gesture-tap-button"};let Ne=class extends ae{constructor(){super(...arguments),this.radios=[],this._sending=new Set,this._learning=!1}_toast(e){this.dispatchEvent(new CustomEvent("hass-notification",{detail:{message:e},bubbles:!0,composed:!0}))}async _call(e,t){try{return await e(),t&&this._toast(t),!0}catch(e){return this._toast(ue(e)),!1}}_currentSettings(){return this._settings??{name:this.device.name,area:this.device.area_id??"",radio:this.device.radio_id}}_settingsChanged(){const e=this._currentSettings();return e.name.trim()!==this.device.name||e.area!==(this.device.area_id??"")||e.radio!==this.device.radio_id}async _saveSettings(){const e=this._currentSettings(),t={};e.name.trim()!==this.device.name&&(t.name=e.name.trim()),e.area!==(this.device.area_id??"")&&(t.area_id=e.area||null),e.radio!==this.device.radio_id&&(t.radio_id=e.radio),await this._call(()=>((e,t,i)=>e.connection.sendMessagePromise({type:"clicker/device/update",device_id:t,...i}))(this.hass,this.device.id,t),"Saved")&&(this._settings=void 0)}_renderSettings(){const e=this._currentSettings(),t=t=>this._settings={...e,...t},i=Object.values(this.hass.areas).sort((e,t)=>e.name.localeCompare(t.name)),s=function(e,t){return t.filter(t=>t.frequency_hz===e.frequency_hz).sort((t,i)=>t.id===e.radio_id?-1:i.id===e.radio_id?1:t.name.localeCompare(i.name))}(this.device,this.radios);return I`
      <div class="card">
        <div class="card-title">Device</div>
        <div class="settings">
          <label
            >Name
            <input
              .value=${e.name}
              @input=${e=>t({name:e.target.value})}
          /></label>
          <label
            >Area
            <select @change=${e=>t({area:e.target.value})}>
              <option value="" ?selected=${!e.area}>No area</option>
              ${i.map(t=>I`<option value=${t.area_id} ?selected=${t.area_id===e.area}>
                  ${t.name}
                </option>`)}
            </select></label
          >
          <label
            >Radio
            <select @change=${e=>t({radio:e.target.value})}>
              ${s.map(t=>I`<option value=${t.id} ?selected=${t.id===e.radio}>
                  ${Ee(t.name,t.frequency_hz)}${t.online?"":" (offline)"}
                </option>`)}
            </select></label
          >
        </div>
        <div class="actions">
          ${this.device.ha_device_id?I`<a class="link" href="/config/devices/device/${this.device.ha_device_id}"
                >Open in Home Assistant</a
              >`:W}
          <span class="spacer"></span>
          ${this._settingsChanged()?I`<button @click=${()=>this._settings=void 0}>Cancel</button>
                <button class="primary" ?disabled=${!e.name.trim()} @click=${this._saveSettings}>
                  Save
                </button>`:W}
        </div>
      </div>
    `}async _test(e){this._sending=new Set([...this._sending,e.id]),await this._call(()=>{return t=this.hass,i=this.device.id,s=e.id,t.connection.sendMessagePromise({type:"clicker/command/send",device_id:i,command_id:s});var t,i,s},`Sent ${e.name}`),this._sending=new Set([...this._sending].filter(t=>t!==e.id))}async _saveCommand(){const e=this._editing,t=this.device.commands.find(t=>t.id===e.id);if(!t)return;const i={};e.name.trim()!==t.name&&(i.name=e.name.trim()),e.kind!==t.kind&&(i.kind=e.kind),e.frames!==t.frames_on_air&&(i.frames_on_air=e.frames),Object.keys(i).length?await this._call(()=>((e,t,i,s)=>e.connection.sendMessagePromise({type:"clicker/command/update",device_id:t,command_id:i,...s}))(this.hass,this.device.id,e.id,i),"Saved")&&(this._editing=void 0):this._editing=void 0}async _delete(e){await this._call(()=>{return t=this.hass,i=this.device.id,s=e.id,t.connection.sendMessagePromise({type:"clicker/command/delete",device_id:i,command_id:s});var t,i,s},`Deleted ${e.name}`)&&(this._confirmDelete=void 0)}_renderCommands(){const e=function(e){const t=new Map;for(const i of e.bindings)for(const[e,s]of Object.entries(i.roles)){const n=t.get(s)??[];n.push({bindingName:i.name,platform:i.platform,role:e}),t.set(s,n)}return t}(this.device);return I`
      <div class="card">
        <div class="card-title">
          Commands <span class="meta">${this.device.commands.length}</span>
          <span class="spacer"></span>
          ${this._learning?W:I`<button @click=${()=>this._learning=!0}>
                <ha-icon icon="mdi:plus"></ha-icon> Learn
              </button>`}
        </div>
        ${this.device.commands.length?this.device.commands.map(t=>this._renderCommand(t,e.get(t.id)??[])):I`<div class="meta">No commands yet. Press Learn, then press buttons on the remote.</div>`}
      </div>
    `}_renderCommand(e,t){if(this._editing?.id===e.id)return this._renderEditor(this._editing);const i=this._confirmDelete===e.id,s=this._sending.has(e.id);return I`
      <div class="row ${i?"confirming":""}">
        <div class="row-main">
          <div class="row-name">${e.name}</div>
          <div class="meta">
            ${Oe[e.kind]} ·
            ${e.encoded?`${e.bits?.length??0}-bit ${e.encoding}`:"raw"} ·
            ${1===e.frames_on_air?"sent once":`${e.frames_on_air} frames`}
            ${t.length?I` · used by ${Re(t)}`:W}
          </div>
          ${i?I`<div class="confirm">
                ${t.length?I`Delete ${e.name}? ${Re(t)} will lose it, and an
                    entity that can't work without it is removed.`:I`Delete ${e.name}? You'd need to learn it again.`}
                <div class="actions">
                  <span class="spacer"></span>
                  <button @click=${()=>this._confirmDelete=void 0}>Cancel</button>
                  <button class="danger" @click=${()=>this._delete(e)}>Delete</button>
                </div>
              </div>`:W}
        </div>
        ${i?W:I`<button ?disabled=${s} @click=${()=>this._test(e)}>
                ${s?"Sending…":"Test"}
              </button>
              <button
                class="icon"
                aria-label="Edit ${e.name}"
                @click=${()=>this._editing={id:e.id,name:e.name,kind:e.kind,frames:e.frames_on_air}}
              >
                <ha-icon icon="mdi:pencil"></ha-icon>
              </button>
              <button
                class="icon"
                aria-label="Delete ${e.name}"
                @click=${()=>this._confirmDelete=e.id}
              >
                <ha-icon icon="mdi:delete-outline"></ha-icon>
              </button>`}
      </div>
    `}_renderEditor(e){const t=t=>this._editing={...e,...t},i=Number.isInteger(e.frames)&&e.frames>=1&&e.frames<=64;return I`
      <div class="row editing">
        <div class="editor">
          <label
            >Name
            <input
              .value=${e.name}
              @input=${e=>t({name:e.target.value})}
          /></label>
          <label
            >Kind
            <select @change=${e=>t({kind:e.target.value})}>
              ${Object.entries(Oe).map(([t,i])=>I`<option value=${t} ?selected=${t===e.kind}>
                  ${i}
                </option>`)}
            </select>
            <span class="hint">${Pe[e.kind]}</span></label
          >
          <label
            >Frames on air
            <input
              type="number"
              min="1"
              max="64"
              .value=${String(e.frames)}
              @input=${e=>t({frames:Number(e.target.value)})}
            />
            <span class="hint ${i?"":"error"}"
              >${i?"1 sends once; 8 is a short press":"Enter 1 to 64"}</span
            ></label
          >
        </div>
        <div class="actions">
          <span class="spacer"></span>
          <button @click=${()=>this._editing=void 0}>Cancel</button>
          <button class="primary" ?disabled=${!e.name.trim()||!i} @click=${this._saveCommand}>
            Save
          </button>
        </div>
      </div>
    `}async _removeBinding(e){await this._call(()=>{return t=this.hass,i=this.device.id,s=e.id,t.connection.sendMessagePromise({type:"clicker/binding/delete",device_id:i,binding_id:s});var t,i,s},`Removed ${e.name}`)&&(this._confirmRemove=void 0)}_renderEntities(){const e="new"===this._editingBinding;return I`
      <div class="card">
        <div class="card-title">
          Entities <span class="spacer"></span>
          ${this._editingBinding||!this.device.commands.length?W:I`<button @click=${()=>this._editingBinding="new"}>
                <ha-icon icon="mdi:plus"></ha-icon> Add
              </button>`}
        </div>
        ${e?I`<clicker-entity-editor
              .hass=${this.hass}
              .device=${this.device}
              @close=${()=>this._editingBinding=void 0}
            ></clicker-entity-editor>`:W}
        ${this.device.bindings.length?this.device.bindings.map(e=>this._renderBinding(e)):e?W:I`<div class="meta">
                ${this.device.commands.length?"No entities yet. Add one to control this device from Home Assistant.":"Learn some commands first, then add entities built from them."}
              </div>`}
      </div>
    `}_renderBinding(e){if(this._editingBinding===e.id)return I`<div class="binding">
        <clicker-entity-editor
          .hass=${this.hass}
          .device=${this.device}
          .binding=${e}
          @close=${()=>this._editingBinding=void 0}
        ></clicker-entity-editor>
      </div>`;const{template:t}=we(e),i=this._confirmRemove===e.id,s=e.entity_ids.length?e.entity_ids:[void 0];return I`
      <div class="binding">
        <div class="entity">
          <ha-icon .icon=${Me[e.platform]??"mdi:remote"}></ha-icon>
          <div class="row-main">
            <div>${e.name}</div>
            <div class="meta">${t.label}</div>
          </div>
          ${i?W:I`<button
                  class="icon"
                  aria-label="Edit ${e.name}"
                  @click=${()=>this._editingBinding=e.id}
                >
                  <ha-icon icon="mdi:pencil"></ha-icon>
                </button>
                <button
                  class="icon"
                  aria-label="Remove ${e.name}"
                  @click=${()=>this._confirmRemove=e.id}
                >
                  <ha-icon icon="mdi:delete-outline"></ha-icon>
                </button>`}
        </div>
        ${s.map(e=>{const t=e?this.hass.states[e]:void 0;return I`<div class="entity-state-row meta">
            <span>${e??"Not created yet"}</span><span>${Ce(t)}</span>
          </div>`})}
        ${i?I`<div class="confirm">
              Remove the ${e.name} ${"button"===e.platform?"buttons":e.platform}?
              ${"button"===e.platform?"Their":"Its"} commands stay on the device.
              <div class="actions">
                <span class="spacer"></span>
                <button @click=${()=>this._confirmRemove=void 0}>Cancel</button>
                <button class="danger" @click=${()=>this._removeBinding(e)}>Remove</button>
              </div>
            </div>`:W}
      </div>
    `}render(){return I`
      <div class="layout">
        <div class="column">${this._renderCommands()}</div>
        <div class="column">
          ${this._learning?I`<clicker-learn-drawer
                .hass=${this.hass}
                .device=${this.device}
                @close=${()=>this._learning=!1}
              ></clicker-learn-drawer>`:W}
          ${this._renderSettings()} ${this._renderEntities()}
        </div>
      </div>
    `}};Ne.styles=[ve,r`
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
      .binding {
        padding: 6px 0;
        border-top: 1px solid var(--divider-color);
      }
      .binding:first-of-type {
        border-top: none;
      }
      .entity-state-row {
        display: flex;
        justify-content: space-between;
        padding-left: 30px;
      }
      .entity ha-icon {
        color: var(--state-icon-color, var(--secondary-text-color));
      }
    `],e([pe({attribute:!1})],Ne.prototype,"hass",void 0),e([pe({attribute:!1})],Ne.prototype,"device",void 0),e([pe({attribute:!1})],Ne.prototype,"radios",void 0),e([me()],Ne.prototype,"_editing",void 0),e([me()],Ne.prototype,"_confirmDelete",void 0),e([me()],Ne.prototype,"_sending",void 0),e([me()],Ne.prototype,"_settings",void 0),e([me()],Ne.prototype,"_learning",void 0),e([me()],Ne.prototype,"_editingBinding",void 0),e([me()],Ne.prototype,"_confirmRemove",void 0),Ne=e([ce("clicker-device-page")],Ne);const Te={fan:"mdi:fan",light:"mdi:lightbulb",switch:"mdi:toggle-switch-variant",button:"mdi:gesture-tap-button"};let Ue=class extends ae{constructor(){super(...arguments),this.narrow=!1}updated(e){e.has("hass")&&this.hass&&!this._unsubscribe&&this._subscribe()}connectedCallback(){super.connectedCallback(),this.hass&&!this._unsubscribe&&this._subscribe()}disconnectedCallback(){super.disconnectedCallback(),this._unsubscribe?.then(e=>e()).catch(()=>{}),this._unsubscribe=void 0}_subscribe(){this._unsubscribe=this.hass.connection.subscribeMessage(e=>{this._data=e,this._error=void 0},{type:"clicker/data/subscribe"}),this._unsubscribe.catch(e=>{this._error=e.message??"Clicker isn't responding. Check that it's loaded.",this._unsubscribe=void 0})}_navigate(e){history.pushState(null,"",`${this.route?.prefix??"/clicker"}${e}`),window.dispatchEvent(new CustomEvent("location-changed",{detail:{replace:!1}}))}get _deviceId(){return/^\/device\/([^/]+)/.exec(this.route?.path??"")?.[1]}render(){const e=this._deviceId,t=e?this._data?.devices.find(t=>t.id===e):void 0;return e&&this._data&&this.hass?I`
        <div class="toolbar">
          <button class="back" aria-label="Back to devices" @click=${()=>this._navigate("")}>
            <ha-icon icon="mdi:arrow-left"></ha-icon>
          </button>
          <div class="title">${t?.name??"Device not found"}</div>
        </div>
        <div class="content">
          ${t?I`<clicker-device-page
                .hass=${this.hass}
                .device=${t}
                .radios=${this._data.radios}
              ></clicker-device-page>`:I`<p class="notice">This device was deleted.</p>`}
        </div>
      `:I`
      <div class="toolbar">
        <ha-menu-button .hass=${this.hass} .narrow=${this.narrow}></ha-menu-button>
        <div class="title">Clicker</div>
      </div>
      <div class="content">${this._renderBody()}</div>
    `}_renderBody(){if(this._error)return I`<p class="notice error">${this._error}</p>`;if(!this._data||!this.hass)return I`<p class="notice">Loading…</p>`;const{devices:e,radios:t,problems:i}=this._data;if(!e.length)return I`<div class="empty">
        <h2>Set up your first remote</h2>
        <p>Clicker learns your RF remotes' buttons and turns them into fans, lights, switches and buttons.</p>
        <p class="hint">${t.length?`Radios ready: ${t.map(e=>`${e.name}`).join(", ")}.`:"No radios yet. Clicker finds ESPHome radios with an RF transmitter or receiver."}</p>
      </div>`;const s=new Map(t.map(e=>[e.id,e]));return I`
      ${i.length?I`<div class="problems">${i.map(e=>I`<div>${e}</div>`)}</div>`:W}
      ${function(e,t,i="No area"){const s=new Map;for(const n of e){const e=n.area_id&&t[n.area_id]?n.area_id:null;let o=s.get(e);o||(o={areaId:e,name:e?t[e].name:i,devices:[]},s.set(e,o)),o.devices.push(n)}const n=(e,t)=>e.name.localeCompare(t.name,void 0,{sensitivity:"base"}),o=[...s.values()].sort((e,t)=>null===e.areaId?1:null===t.areaId?-1:n(e,t));for(const e of o)e.devices.sort(n);return o}(e,this.hass.areas).map(e=>I`
          <h2 class="area">${e.name}</h2>
          <div class="grid">
            ${e.devices.map(e=>this._renderDevice(e,s.get(e.radio_id)))}
          </div>
        `)}
    `}_renderDevice(e,t){const i=e.bindings.flatMap(e=>(e.entity_ids.length?e.entity_ids:[void 0]).map(t=>({binding:e,entityId:t})));return I`
      <div
        class="card clickable"
        role="button"
        tabindex="0"
        @click=${()=>this._navigate(`/device/${e.id}`)}
        @keydown=${t=>"Enter"===t.key&&this._navigate(`/device/${e.id}`)}
      >
        <div class="card-head">
          <span class="name">${e.name}</span>
          ${t?.online?W:I`<span class="badge warning">${t?"Radio offline":"No radio"}</span>`}
        </div>
        <div class="meta">
          ${Ee(t?.name,e.frequency_hz)} ·
          ${function(e,t,i=`${t}s`){return`${e} ${1===e?t:i}`}(e.commands.length,"command")}
        </div>
        ${i.length?I`<div class="entities">
              ${i.map(({binding:e,entityId:t})=>{const i=t?this.hass.states[t]:void 0,s=i?.attributes.friendly_name??e.name;return I`<div class="entity">
                  <ha-icon .icon=${Te[e.platform]??"mdi:remote"}></ha-icon>
                  <span class="entity-name">${s}</span>
                  <span class="entity-state">${Ce(i)}</span>
                </div>`})}
            </div>`:I`<div class="meta">No entities yet</div>`}
      </div>
    `}};Ue.styles=r`
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
  `,e([pe({attribute:!1})],Ue.prototype,"hass",void 0),e([pe({type:Boolean})],Ue.prototype,"narrow",void 0),e([pe({attribute:!1})],Ue.prototype,"route",void 0),e([me()],Ue.prototype,"_data",void 0),e([me()],Ue.prototype,"_error",void 0),Ue=e([ce("clicker-panel")],Ue);export{Ue as ClickerPanel};
