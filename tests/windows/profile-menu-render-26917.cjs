// Packed 26.917 contract: native bindings and synthetic accounts only.
const assert = require('node:assert/strict');
const vm = require('node:vm');
const path = require('node:path');

module.exports = async function verify26917({asar, archive, entries, primary, initial, extractFunction}) {
  const read = name => asar.extractFile(archive, name.replace(/^\//, '').split('/').join(path.sep)).toString();
  assert.match(initial, /Pf as Jr[,}]/);
  const shared = read(entries.find(p => /\/app-shared-[a-f0-9]+\.js$/.test(p)));
  assert.match(shared, /LeftIcon:n,leftIconAsset:f/);
  assert.match(initial, /M4\.jsx\)\(Jr,\{leftIconAsset:Ge/);
  assert.match(initial, /function CodexMuxRouterIcon\(e\)/);
  assert.match(initial, /function CodexMuxAccountMenu\(\)/);
  assert.match(initial, /Se=\(0,H\$\.jsxs\)\(H\$\.Fragment,\{children:\[Se,window\.__codexMuxResetAccountSelector\?\?null\]\}\)/);
  assert.match(initial, /usageItems:\(0,M4\.jsx\)\(CodexMuxAccountMenu,\{\}\)/);
  assert.equal(initial.split('onOpenChange:CodexMuxProfileMenuOpenChange(A)').length - 1, 2);
  const profile = read(entries.find(p => /\/profile-[a-f0-9]+\.js$/.test(p)));
  assert.match(profile, /CodexMuxProfileAvatarStack\?\.\(\{onSelect:\(\)=>Ke\.refetch\(\)\}\)\?\?null,Yn,Zn/);
  assert.match(initial, /globalThis\.codexMuxProfileData\(globalThis\.__codexMuxSelectedProfileAccountId\?\?null\)/);
  const plugins = entries.filter(p => /\/plugins-settings-[a-f0-9]+\.js$/.test(p)).map(read);
  assert.equal(plugins.filter(p => p.includes('children:[globalThis.CodexMuxPluginScope?.()??null,D]')).length, 1);
  const openSource = extractFunction(initial, 'Nj');
  assert.match(openSource, /\.set\(Ij/);
  assert.match(openSource, /ModalComponent:t,props:n/);
  const start = initial.indexOf('const CODEX_MUX_API =');
  const end = initial.indexOf('function cys(e)', start);
  assert.ok(start >= 0 && end > start);
  const code = initial.slice(start, end);
  assert.doesNotMatch(code, /window\.prompt\(/);
  const jsx = (type, props, key) => {
    assert.ok(typeof type === 'function' || typeof type === 'string', 'valid native component binding');
    return {type, props, key};
  };
  const accounts = [{id:'primary',label:'Primary',enabled:true,connected:true,controller:true}, {id:'second',label:'Subscription 2',enabled:true,connected:true}];
  for (const brokenOpener of [false, true]) {
    const values = [accounts,false,'','','',null,false,'second'];
    let index = 0, state = {modals:[],nextKey:1}, initialized = false;
    const calls = [], invalidations = [];
    const scope = {set:(_atom, update)=>{state=update(state);}};
    const c = vm.createContext({
      AbortController, TextDecoder, TextEncoder, setTimeout, clearTimeout, setInterval, clearInterval,
      document:{querySelector:()=>({focus(){}})},window:{prompt(){throw Error('unsupported prompt');}},
      M4:{jsx,jsxs:jsx,Fragment:'fragment'}, Ar:()=>scope, X:{}, mIo:()=>{initialized=true;}, uIo:()=>{}, Jr:()=>{}, co:{Separator:()=>{}}, CodexMuxRouterIcon:()=>{},
      Ij:{}, Dpr:(a,b)=>a===b, noop:()=>{}, ads:()=>{},
      mys:{useState:initial=>{const slot=index++;if(!(slot in values))values[slot]=typeof initial==='function'?initial():initial;return [values[slot],next=>{values[slot]=typeof next==='function'?next(values[slot]):next;}];},useCallback:f=>f,useEffect:()=>{}},
      HS:()=>{},cr:()=>{},Yi:o=>o, _: {ONE_MINUTE:60000,FIVE_SECONDS:5000},Bai:x=>x,Vai:()=>{throw Error('unscoped credit read');},
      ut:()=>({setQueryData(){}}),Zg:()=>key=>invalidations.push(key),qa:o=>o,uai:x=>x,Uai:()=>{throw Error('unscoped credit redemption');},
      fetch:async(url, options={})=>{
        calls.push({url,...options});
        if(url.endsWith('/accounts'))return {ok:true,json:async()=>({accounts})};
        assert.match(url,/\/accounts\/second(?:\/rate-limit-resets(?:\/consume)?)?$/);
        return {ok:true,json:async()=>url.endsWith('/consume')?{code:'reset',credit:{id:'fixture-credit'}}:{available_count:1,credits:[{id:'fixture-credit',status:'available'}]}};
      },
    });
    vm.runInContext(openSource,c);
    vm.runInContext(brokenOpener?code.replace('Nj(modalScope, CodexMuxUsageModal, {})','noop(modalScope, CodexMuxUsageModal, {})'):code,c);
    const render=()=>{index=0;return c.CodexMuxAccountMenu().props.children;};
    const find=action=>render().find(row=>row.props['data-codex-mux-action']===action);
    const event={preventDefault(){},stopPropagation(){}};
    find('usage').props.onSelect(event);
    assert.equal(state.modals.length,brokenOpener?0:1);
    if(brokenOpener)continue;
    const close=()=>{};
    const view=state.modals[0].ModalComponent({onClose:close});
    assert.equal(initialized,true);assert.equal(view.type,c.uIo);assert.equal(view.props.onClose,close);
    assert.equal(calls.length,0,'opening the dialog cannot redeem a credit');
    find('rename').props.onSelect(event);
    find('rename-form').props.children[1].props.onChange({target:{value:'Personal'}});
    await find('rename-form').props.onSubmit(event);
    assert.equal(calls[0].method,'PATCH');assert.equal(JSON.parse(calls[0].body).label,'Personal');
    assert.ok(calls[0].headers['X-Codex-Mux-Token']);
    vm.runInContext(extractFunction(initial,'zai')+';'+extractFunction(initial,'Hai'),c);
    c.window.__codexMuxResetAccountId='second';
    const query=c.zai();assert.equal(query.queryKey[1],'second');
    assert.equal((await query.queryFn()).available_count,1);
    const mutation=c.Hai();c.window.__codexMuxResetAccountId='primary';
    const input={creditId:'fixture-credit',redeemRequestId:'fixture-request'};
    const result=await mutation.mutationFn(input);mutation.onSuccess(result,input);
    assert.match(calls.at(-1).url,/\/accounts\/second\/rate-limit-resets\/consume$/);
    assert.deepEqual(JSON.parse(calls.at(-1).body),input);
    assert.ok(invalidations.some(key=>key[1]==='second'));
    find('routing-mode').props.onSelect(event);
    assert.equal(render().find(row=>row.props.id==='codex-mux-routing-options').props.children.length,3);
  }
  const threadPath=entries.find(p=>/\/local-conversation-thread-[a-f0-9]+\.js$/.test(p)&&read(p).includes('const CODEX_MUX_THREAD_API ='));
  assert.ok(threadPath);
  const thread=read(threadPath);
  assert.match(thread,/const CodexMuxThreadReact=ft\(\);/);
  assert.match(thread,/const route = J\(bl\);/);
  assert.match(thread,/children:\[M,x,N,P,\(0,DE\.jsx\)\(CodexMuxThreadSubscription,\{\}\),j,F\]/);
  const component=thread.slice(thread.indexOf('const CODEX_MUX_THREAD_API ='),thread.indexOf('function CE(e)'));
  assert.match(component,/\/thread-spending\?threadId=/);
  for(const spending of [null,{threadId:'task',request:{accountId:'second'},account:{id:'second',label:'Subscription 2'}}]){
    const c=vm.createContext({ft:()=>({useState:()=>[spending,()=>{}],useEffect:()=>{}}),J:()=>({value:{routeKind:'local-thread',conversationId:'task'}}),bl:{},DE:{jsx,jsxs:jsx},Z:{Section:()=>{}}});
    vm.runInContext(component,c);
    const rendered=c.CodexMuxThreadSubscription();assert.equal(rendered.props.title,'Subscription');
    if(spending)assert.match(JSON.stringify(rendered),/Subscription 2/);
  }
  console.log('PASS: 26.917 native menu, Rename, Usage/reset scoped requests, Auto selector, profile/plugins and last-request display.');
};
