"""Exact 26.915 renderer profile: account UI now lives in app-initial."""
import json
from pathlib import Path
import re

from windows_renderer_26903 import usage_modal_opener_alias


def replace(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise RuntimeError(f"26.915 anchor count {text.count(old)}: {old[:100]}")
    return text.replace(old, new, 1)


def remap(text: str, names: dict[str, str]) -> str:
    # One pass avoids cascading aliases, notably the native store named '$'.
    for name in names:
        if not re.search(r"(?<![\w$])" + re.escape(name) + r"(?![\w$])", text):
            raise RuntimeError(f"Unused router binding: {name}")
    return re.sub(r"[A-Za-z_$][\w$]*", lambda m: names.get(m[0], m[0]), text)


def account_menu_item_alias(source: str) -> str:
    matches = re.findall(r'\(0,d6\.jsx\)\(([\w$]+),\{leftIconAsset:Hee,"aria-label":e,className:`opacity-50`,disabled:n,onSelect:r,children:h\},`email`\)', source)
    if len(matches) != 1:
        raise RuntimeError(f"Expected one 26.915 native menu item, found {len(matches)}")
    return matches[0]


def patch_renderer(extracted: Path, token: str, control_port: int) -> None:
    if json.loads((extracted / "package.json").read_text(encoding="utf-8"))["version"] != "26.915.31945":
        raise RuntimeError("Unsupported initial renderer version")
    assets = extracted / "webview/assets"
    root = Path(__file__).resolve().parent.parent

    def one(pattern: str, marker: str = "") -> Path:
        matches = [p for p in assets.glob(pattern) if marker in p.read_text(encoding="utf-8")]
        if len(matches) != 1:
            raise RuntimeError(f"Expected one 26.915 {pattern}, found {len(matches)}")
        return matches[0]

    index = extracted / "webview/index.html"
    index.write_text(replace(index.read_text(encoding="utf-8"), "connect-src &#39;self&#39;",
                             f"connect-src &#39;self&#39; http://127.0.0.1:{control_port}"), encoding="utf-8")
    initial_path = one("app-initial-*.js")
    initial = initial_path.read_text(encoding="utf-8")
    component = (root / "ui/account-menu.js").read_text(encoding="utf-8")
    component = remap(component, {"e7":"d6", "kXc":"F6s", "QLs":"$ms", "Lo":"xf", "Q":"$",
                                 "BW":usage_modal_opener_alias(initial, "$ms"), "_H":account_menu_item_alias(initial),
                                 "CH":"iV", "jLa":"MQs", "S2":"u_s"})
    component = component.replace("__CODEX_MUX_CONTROL_PORT__", str(control_port)).replace("__CODEX_MUX_CONTROL_TOKEN__", token)
    # Rolldown now emits self-replacing lazy functions. Initialize the real native
    # modules, never substitute an analytics alias or a guessed React export.
    for anchor in ("function d_s(){return(d_s=n((()=>{X(),l_s=K(),u_s=e=>", "function rhs(){return(rhs=n((()=>{ehs=G()"):
        if initial.count(anchor) != 1:
            raise RuntimeError("Native icon/modal initializer changed")
    component = replace(component, "function CodexMuxAccountMenu() {", "function CodexMuxAccountMenu() {\n  d_s();")
    component = replace(component, "function CodexMuxUsageModal({\n  onClose,\n}) {", "function CodexMuxUsageModal({\n  onClose,\n}) {\n  rhs();")
    for old, new in {"list-apps":"app/list", "list-installed-apps":"app/installed", "read-apps":"app/read",
                     "list-mcp-server-status":"mcpServerStatus/list", "login-mcp-server":"mcpServer/oauth/login"}.items():
        component = replace(component, f'"{old}"', f'"{new}"')
    component += "\n" + "\n".join(f"globalThis.{name}={name};" for name in (
        "codexMuxScopePluginRequest", "codexMuxProfileData", "codexMuxRateLimitResets", "codexMuxConsumeRateLimitReset")) + "\n"
    anchor = "function k6s(e){let t=(0,P6s.c)(258),{hasAmbientUsageSubtext:n,sidebarFooter:r,triggerButton:i}=e"
    initial = replace(initial, anchor, component + anchor)
    initial = replace(initial, "usageItems:Vt", "usageItems:(0,d6.jsx)(CodexMuxAccountMenu,{})")
    for old in ("sideOffset:6,triggerButton:Gt,onOpenChange:j,children:[M,null]",
                "open:l,onOpenChange:j,contentWidth:`panel`,triggerButton:Gt,children:rn"):
        initial = replace(initial, old, old.replace("onOpenChange:j", "onOpenChange:CodexMuxProfileMenuOpenChange(j)"))
    anchor = "function $ms(e){let t=(0,ehs.c)(20),{defaultResetCreditsOpen:n,initialAvailableCount:r,isRateLimitReached:i,onClose:a,onResetComplete:o}=e"
    initial = replace(initial, anchor, anchor.replace("{let t=", "{CodexMuxUseResetAccountState();let t="))
    anchor = "let v=_,y;return t[13]!==n||t[14]!==d||t[15]!==g||t[16]!==v||t[17]!==r||t[18]!==m?(y=(0,nhs.jsx)(Gms,{defaultResetCreditsOpen:n,errorMessage:d,initialAvailableCount:r,isResetting:m,onClose:g,onResetCredit:v}),t[13]=n,t[14]=d,t[15]=g,t[16]=v,t[17]=r,t[18]=m,t[19]=y):y=t[19],y}"
    initial = replace(initial, anchor, "let v=_;return (0,nhs.jsx)(Gms,{defaultResetCreditsOpen:n,errorMessage:d,initialAvailableCount:r,isResetting:m,onClose:g,onResetCredit:v})}")
    initial = replace(initial, "let y=v;if(g!=null){", "let y=window.__codexMuxSelectedUsageWindows??v;if(g!=null){")
    anchor = 'let Se=I.length===2?`h-[140px]`:`h-[70px]`,Ce;'
    initial = replace(initial, anchor, 'xe=(0,B0.jsxs)(B0.Fragment,{children:[xe,window.__codexMuxResetAccountSelector??null]});' + anchor)
    anchor = "async sendRequest(e,t,n){if(this.dispatchMessage==null)throw Error(`AppServerRequestClient is missing a message dispatcher`);"
    initial = replace(initial, anchor, anchor.replace("{if(", "{t=globalThis.codexMuxScopePluginRequest?.(e,t)??t;if("))
    initial = replace(initial, "let e=await oy.safeGet(`/wham/profiles/me`)", "let e=await(globalThis.codexMuxProfileData?globalThis.codexMuxProfileData(globalThis.__codexMuxSelectedProfileAccountId??null):oy.safeGet(`/wham/profiles/me`))")
    query = "function mSi(){let e=(0,VR.c)(1);XC(),vf(null);let t;return e[0]===Symbol.for(`react.memo_cache_sentinel`)?(t={queryKey:[`rate-limit-reset-credits`],queryFn:gSi,select:hSi,refetchInterval:kv.ONE_MINUTE,staleTime:kv.FIVE_SECONDS},e[0]=t):t=e[0],Jf(t)}"
    initial = replace(initial, query, "function mSi(){XC();vf(null);let e=window.__codexMuxResetAccountId;return Jf({queryKey:[`rate-limit-reset-credits`,e??`primary`],queryFn:e?()=>globalThis.codexMuxRateLimitResets(e):gSi,select:hSi,refetchInterval:kv.ONE_MINUTE,staleTime:kv.FIVE_SECONDS})}")
    mutation = "function _Si(){let e=(0,VR.c)(3),t=Kf(),n=Dv(),r;return e[0]!==n||e[1]!==t?(r={mutationFn:vSi,onSuccess:(e,r)=>{let{creditId:i}=r,a=e.code;if(a===`reset`||a===`already_redeemed`){let n=e.code===`reset`?e.credit?.id??i:i;t.setQueryData([`rate-limit-reset-credits`],e=>$bi(e,a,n))}Promise.all([n([`rate-limit-status`]),n([`rate-limit-reset-credits`])])}},e[0]=n,e[1]=t,e[2]=r):r=e[2],Zf(r)}"
    initial = replace(initial, mutation, "function _Si(){let e=Kf(),t=Dv(),n=window.__codexMuxResetAccountId,r=[`rate-limit-reset-credits`,n??`primary`];return Zf({mutationFn:n?i=>globalThis.codexMuxConsumeRateLimitReset(n,i):vSi,onSuccess:(n,i)=>{let{creditId:a}=i,o=n.code;if(o===`reset`||o===`already_redeemed`){let t=o===`reset`?n.credit?.id??a:a;e.setQueryData(r,e=>$bi(e,o,t))}Promise.all([t([`rate-limit-status`]),t(r)])}})}")
    initial_path.write_text(initial, encoding="utf-8")
    primary_path = one("app-primary-*.js")
    primary = primary_path.read_text(encoding="utf-8")
    for message in ("You’re out of Codex and Work usage", "You’ve used all Codex and Work usage", "You’ve reached your usage limit"):
        primary = replace(primary, f"defaultMessage:`{message}`", "defaultMessage:`All connected subscriptions are depleted`")
    primary_path.write_text(primary, encoding="utf-8")

    profile_path = one("profile-*.js", 'className:`relative isolate flex flex-col items-center`')
    profile = profile_path.read_text(encoding="utf-8")
    anchor = 'let $n;t[192]!==Xn||t[193]!==Qn?($n=(0,$.jsx)(`section`,{"aria-busy":Xn,className:`relative isolate flex flex-col items-center`,children:Qn}),t[192]=Xn,t[193]=Qn,t[194]=$n):$n=t[194];'
    # Keep the redesigned public-profile/editing UI. The account selector is an
    # independent sibling; legacy profile stats still refresh the scoped query.
    profile = replace(profile, anchor, 'let $n=(0,$.jsxs)(`section`,{"aria-busy":Xn,className:`relative isolate flex flex-col items-center`,children:[globalThis.CodexMuxProfileAvatarStack?.({onSelect:()=>Ke.refetch()})??null,Qn]});')
    profile_path.write_text(profile, encoding="utf-8")
    plugins = one("plugins-settings-*.js", "action:F,children:D})")
    plugins.write_text(replace(plugins.read_text(encoding="utf-8"), "action:F,children:D})", "action:F,children:[globalThis.CodexMuxPluginScope?.()??null,D]})"), encoding="utf-8")
    anchor = "function KT(e){let t=(0,YT.c)(42),{onForceShow:n,isVisible:r,registerEnvironmentActionCommands:i,onOpenBackgroundAgent:a,onOpenPullRequestSidePanel:o,onOpenSubagentsPanel:s}=e"
    thread_path = one("local-conversation-thread-*.js", anchor)
    thread = thread_path.read_text(encoding="utf-8")
    component = remap((root / "ui/thread-subscription.js").read_text(encoding="utf-8"),
                      {"$n":"ju", "sr":"il", "TE":"CodexMuxThreadReact", "zE":"XT", "K":"$"})
    component = component.replace("__CODEX_MUX_CONTROL_PORT__", str(control_port)).replace("__CODEX_MUX_CONTROL_TOKEN__", token)
    component = replace(component, "function CodexMuxThreadSubscription() {", "function CodexMuxThreadSubscription() {\n  const CodexMuxThreadReact=et();")
    thread = replace(thread, anchor, component + "\n" + anchor)
    thread = replace(thread, "children:[D,g,O,k,E,A]", "children:[D,g,O,k,(0,XT.jsx)(CodexMuxThreadSubscription,{}),E,A]")
    thread_path.write_text(thread, encoding="utf-8")
