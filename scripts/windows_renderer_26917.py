"""Exact 26.917 Windows renderer profile; fail if any native binding moves."""
import json
from pathlib import Path
import re

from windows_renderer_26915 import remap, replace, usage_modal_opener_alias


def account_menu_item_alias(source: str) -> str:
    matches = re.findall(
        r'\(0,M4\.jsx\)\(([\w$]+),\{leftIconAsset:Ge,"aria-label":e,'
        r'className:`opacity-50`,disabled:n,onSelect:r,children:h\},`email`\)', source
    )
    if len(matches) != 1:
        raise RuntimeError(f"Expected one 26.917 native profile menu item, found {len(matches)}")
    return matches[0]


def patch_renderer(extracted: Path, token: str, control_port: int) -> None:
    if json.loads((extracted / "package.json").read_text(encoding="utf-8"))["version"] != "26.917.51856":
        raise RuntimeError("Unsupported 26.917 renderer version")
    assets = extracted / "webview/assets"
    root = Path(__file__).resolve().parent.parent

    def one(pattern: str, marker: str = "") -> Path:
        matches = [p for p in assets.glob(pattern) if marker in p.read_text(encoding="utf-8")]
        if len(matches) != 1:
            raise RuntimeError(f"Expected one 26.917 {pattern} with marker, found {len(matches)}")
        return matches[0]

    index = extracted / "webview/index.html"
    index.write_text(replace(index.read_text(encoding="utf-8"), "connect-src &#39;self&#39;",
                             f"connect-src &#39;self&#39; http://127.0.0.1:{control_port}"), encoding="utf-8")
    initial_path = one("app-initial-*.js")
    initial = initial_path.read_text(encoding="utf-8")
    for anchor in (
        "function _ys(){return(_ys=n((()=>{pys=c()",
        "function mIo(){return(mIo=n((()=>{dIo=c()",
        "function ads(e){return ods(e).src}",
        "function Nj(e,t,n,r){e.set(Ij",
        "function cys(e){let t=(0,pys.c)(259)",
    ):
        if initial.count(anchor) != 1:
            raise RuntimeError(f"26.917 native menu binding changed: {anchor[:50]}")

    component = (root / "ui/account-menu.js").read_text(encoding="utf-8")
    component = remap(component, {
        "e7": "M4", "kXc": "mys", "QLs": "uIo", "Lo": "Ar", "Q": "X",
        "BW": usage_modal_opener_alias(initial, "uIo"), "_H": account_menu_item_alias(initial),
        "CH": "co", "jLa": "ads", "S2": "CodexMuxRouterIcon",
    })
    component = component.replace("__CODEX_MUX_CONTROL_PORT__", str(control_port)).replace("__CODEX_MUX_CONTROL_TOKEN__", token)
    component = replace(component, "function CodexMuxUsageModal({\n  onClose,\n}) {",
                        "function CodexMuxUsageModal({\n  onClose,\n}) {\n  mIo();")
    for old, new in {"list-apps":"app/list", "list-installed-apps":"app/installed", "read-apps":"app/read",
                     "list-mcp-server-status":"mcpServerStatus/list", "login-mcp-server":"mcpServer/oauth/login"}.items():
        component = replace(component, f'"{old}"', f'"{new}"')
    component += "\n" + "\n".join(f"globalThis.{name}={name};" for name in (
        "codexMuxScopePluginRequest", "codexMuxProfileData", "codexMuxRateLimitResets", "codexMuxConsumeRateLimitReset")) + "\n"
    icon = ("function CodexMuxRouterIcon(e){return(0,M4.jsx)(`svg`,{viewBox:`0 0 20 20`,fill:`none`,"
            "\"aria-hidden\":!0,...e,children:(0,M4.jsx)(`path`,{d:`M3 14.5h14M5 12V8m5 4V4m5 8V6`,"
            "stroke:`currentColor`,strokeWidth:1.5,strokeLinecap:`round`})})}\n")
    anchor = "function cys(e){let t=(0,pys.c)(259),{hasAmbientUsageSubtext:n,sidebarFooter:r,triggerButton:i}=e"
    initial = replace(initial, anchor, icon + component + anchor)
    initial = replace(initial, "usageItems:Ht", "usageItems:(0,M4.jsx)(CodexMuxAccountMenu,{})")
    for old in ("sideOffset:6,triggerButton:Kt,onOpenChange:A,children:[M,null]",
                "open:l,onOpenChange:A,contentWidth:`panel`,triggerButton:Kt,children:an"):
        initial = replace(initial, old, old.replace("onOpenChange:A", "onOpenChange:CodexMuxProfileMenuOpenChange(A)"))

    reset = "function uIo(e){let t=(0,dIo.c)(19),{defaultResetCreditsOpen:n,initialAvailableCount:r,isRateLimitReached:i,onClose:a,onResetComplete:o}=e"
    initial = replace(initial, reset, reset.replace("{let t=", "{CodexMuxUseResetAccountState();let t="))
    cached = ("let _=g,v;return t[12]!==n||t[13]!==u||t[14]!==h||t[15]!==_||t[16]!==r||t[17]!==p?"
              "(v=(0,pIo.jsx)(nIo,{defaultResetCreditsOpen:n,errorMessage:u,initialAvailableCount:r,isResetting:p,"
              "onClose:h,onResetCredit:_}),t[12]=n,t[13]=u,t[14]=h,t[15]=_,t[16]=r,t[17]=p,t[18]=v):v=t[18],v}")
    initial = replace(initial, cached, "let _=g;return (0,pIo.jsx)(nIo,{defaultResetCreditsOpen:n,errorMessage:u,initialAvailableCount:r,isResetting:p,onClose:h,onResetCredit:_})}")
    initial = replace(initial, "let y=v;if(g!=null){", "let y=window.__codexMuxSelectedUsageWindows??v;if(g!=null){")
    header = "let Ce=I.length===2?`h-[140px]`:`h-[70px]`,we;"
    initial = replace(initial, header, "Se=(0,H$.jsxs)(H$.Fragment,{children:[Se,window.__codexMuxResetAccountSelector??null]});" + header)
    request = "async sendRequest(e,t,n){if(this.dispatchMessage==null)throw Error(`AppServerRequestClient is missing a message dispatcher`);"
    initial = replace(initial, request, request.replace("{if(", "{t=globalThis.codexMuxScopePluginRequest?.(e,t)??t;if("))
    initial = replace(initial, "let e=await vg.safeGet(`/wham/profiles/me`)",
                      "let e=await(globalThis.codexMuxProfileData?globalThis.codexMuxProfileData(globalThis.__codexMuxSelectedProfileAccountId??null):vg.safeGet(`/wham/profiles/me`))")
    query = ("function zai(){let e=(0,uz.c)(1);HS(),cr(null);let t;return e[0]===Symbol.for(`react.memo_cache_sentinel`)?"
             "(t={queryKey:[`rate-limit-reset-credits`],queryFn:Vai,select:Bai,refetchInterval:_.ONE_MINUTE,"
             "staleTime:_.FIVE_SECONDS},e[0]=t):t=e[0],Yi(t)}")
    initial = replace(initial, query, "function zai(){HS();cr(null);let e=window.__codexMuxResetAccountId;return Yi({queryKey:[`rate-limit-reset-credits`,e??`primary`],queryFn:e?()=>globalThis.codexMuxRateLimitResets(e):Vai,select:Bai,refetchInterval:_.ONE_MINUTE,staleTime:_.FIVE_SECONDS})}")
    mutation = ("function Hai(){let e=(0,uz.c)(3),t=ut(),n=Zg(),r;return e[0]!==n||e[1]!==t?"
                "(r={mutationFn:Uai,onSuccess:(e,r)=>{let{creditId:i}=r,a=e.code;if(a===`reset`||a===`already_redeemed`){"
                "let n=e.code===`reset`?e.credit?.id??i:i;t.setQueryData([`rate-limit-reset-credits`],e=>uai(e,a,n))}"
                "Promise.all([n([`rate-limit-status`]),n([`rate-limit-reset-credits`])])}},e[0]=n,e[1]=t,e[2]=r):r=e[2],qa(r)}")
    initial = replace(initial, mutation, "function Hai(){let e=ut(),t=Zg(),n=window.__codexMuxResetAccountId,r=[`rate-limit-reset-credits`,n??`primary`];return qa({mutationFn:n?i=>globalThis.codexMuxConsumeRateLimitReset(n,i):Uai,onSuccess:(n,i)=>{let{creditId:a}=i,o=n.code;if(o===`reset`||o===`already_redeemed`){let t=o===`reset`?n.credit?.id??a:a;e.setQueryData(r,e=>uai(e,o,t))}Promise.all([t([`rate-limit-status`]),t(r)])}})}")
    initial_path.write_text(initial, encoding="utf-8")

    primary_path = one("app-primary-*.js")
    primary = primary_path.read_text(encoding="utf-8")
    for message in ("You’re out of Codex and Work usage", "You’ve used all Codex and Work usage", "You’ve reached your usage limit"):
        primary = replace(primary, f"defaultMessage:`{message}`", "defaultMessage:`All connected subscriptions are depleted`")
    primary_path.write_text(primary, encoding="utf-8")

    profile_path = one("profile-*.js", 'className:`relative isolate flex flex-col items-center`')
    profile = profile_path.read_text(encoding="utf-8")
    profile = replace(profile, 'Qn=(0,$.jsxs)(`section`,{"aria-busy":Jn,className:`relative isolate flex flex-col items-center`,children:[Yn,Zn]})',
                      'Qn=(0,$.jsxs)(`section`,{"aria-busy":Jn,className:`relative isolate flex flex-col items-center`,children:[globalThis.CodexMuxProfileAvatarStack?.({onSelect:()=>Ke.refetch()})??null,Yn,Zn]})')
    profile_path.write_text(profile, encoding="utf-8")
    plugins = one("plugins-settings-*.js", "action:F,children:D})")
    plugins.write_text(replace(plugins.read_text(encoding="utf-8"), "action:F,children:D})", "action:F,children:[globalThis.CodexMuxPluginScope?.()??null,D]})"), encoding="utf-8")

    anchor = "function CE(e){let t=(0,EE.c)(45),{isHidden:n,onForceShow:r,registerEnvironmentActionCommands:i,onOpenBackgroundAgent:a,onOpenPullRequestSidePanel:o,onOpenSubagentsPanel:s}=e"
    thread_path = one("local-conversation-thread-*.js", anchor)
    thread = thread_path.read_text(encoding="utf-8")
    component = remap((root / "ui/thread-subscription.js").read_text(encoding="utf-8"),
                      {"$n":"J", "sr":"bl", "TE":"CodexMuxThreadReact", "zE":"DE", "K":"Z"})
    component = component.replace("__CODEX_MUX_CONTROL_PORT__", str(control_port)).replace("__CODEX_MUX_CONTROL_TOKEN__", token)
    component = replace(component, "function CodexMuxThreadSubscription() {", "function CodexMuxThreadSubscription() {\n  const CodexMuxThreadReact=ft();")
    thread = replace(thread, anchor, component + "\n" + anchor)
    thread = replace(thread, "children:[M,x,N,P,j,F]", "children:[M,x,N,P,(0,DE.jsx)(CodexMuxThreadSubscription,{}),j,F]")
    thread_path.write_text(thread, encoding="utf-8")
