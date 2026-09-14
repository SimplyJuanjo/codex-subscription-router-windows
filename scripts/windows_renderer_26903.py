"""Fail-closed renderer adaptation for the split 26.903 desktop bundles."""
from pathlib import Path
import re
import json


def account_menu_item_alias(primary: str, updated: bool = False, modern: bool = False) -> str:
    # Bind to the component actually used by the native profile menu. Matching
    # an identifier elsewhere (for example text-xl CSS) can select an unrelated
    # object after minification and cause React error 130 when the menu opens.
    if modern:
        pattern = (r'\(0,Gz\.jsx\)\(([A-Za-z_$][\w$]*),\{leftIconAsset:lE,"aria-label":e,'
                   r'className:`opacity-50`,disabled:n,onSelect:r,children:p\},`email`\)')
    else:
        pattern = (r'\(0,xK\.jsx\)\(([A-Za-z_$][\w$]*),\{LeftIcon:oT,"aria-label":e,' if updated else r'\(0,dq\.jsx\)\(([A-Za-z_$][\w$]*),\{LeftIcon:CT,"aria-label":e,') + r'className:`opacity-50`,disabled:n,onSelect:r,children:f\},`email`\)'
    matches = re.findall(pattern, primary)
    if len(matches) != 1:
        raise RuntimeError(f"expected one native profile menu item binding, found {len(matches)}")
    return matches[0]


def usage_modal_opener_alias(primary: str, modal: str) -> str:
    # Follow the native usage button, not a historical minified alias. In
    # 26.908 the former alias now logs product analytics without opening UI.
    pattern = (r'([A-Za-z_$][\w$]*)\([A-Za-z_$][\w$]*,' + re.escape(modal) +
               r',\{defaultResetCreditsOpen:!0,initialAvailableCount:')
    matches = re.findall(pattern, primary)
    if len(matches) != 1:
        raise RuntimeError(f"expected one native usage modal opener, found {len(matches)}")
    return matches[0]


def patch_renderer(extracted: Path, token: str, control_port: int) -> None:
    assets = extracted / "webview" / "assets"
    root = Path(__file__).resolve().parent.parent
    version = json.loads((extracted / "package.json").read_text(encoding="utf-8"))["version"]
    if version not in {"26.903.61454", "26.903.71938", "26.908.40834"}:
        raise RuntimeError(f"unsupported split renderer version: {version}")
    modern = version == "26.908.40834"
    updated = version == "26.903.71938"
    stage = "primary"
    aliases = {
        "primary": {"dq":"xK", "Pyn":"Obn", "tG":"tfn", "fo":"Oe", "HE":"zb", "Zv":"Hv", "of":"Rd", "uB":"Qz", "MG":"iG", "kyn":"Cbn", "uq":"bK", "Rdn":"nfn", "Bdn":"ifn", "Adn":"qdn", "eG":"VW", "Eb":"bb"},
        "initial": {"vO":"_O", "x5i":"j5i", "sb":"ob", "C5i":"N5i", "S5i":"M5i", "nD":"tD", "gb":"hb", "w5i":"P5i", "fb":"db", "eD":"$E", "T5i":"F5i", "s8i":"_8i", "yb":"vb"},
        "profile": {"St":"xt", "xt":"bt", "M":"N"},
        "thread": {"ve":"s", "ds":"ps", "De":"y"},
    }
    if modern:
        aliases = {
            "primary": {"dq":"Gz", "Pyn":"vGt", "tG":"NL", "fo":"Of", "HE":"o_", "Zv":"Dp", "of":"tS", "uB":"$N", "MG":"cR", "kyn":"pGt", "uq":"Wz", "Rdn":"_It", "Bdn":"yIt", "Adn":"lIt"},
            "initial": {"vO":"DS", "x5i":"iji", "lq":"cG", "dz":"KD", "sb":"fm", "C5i":"oji", "S5i":"aji", "nD":"Qx", "gb":"xm", "w5i":"sji", "fb":"_m", "eD":"Xx", "T5i":"cji", "s8i":"Wki", "yb":"wm"},
            "thread": {"iE":"nO", "sE":"aO", "ve":"vi", "ds":"S", "De":"r", "cE":"oO"},
        }

    def translate(value: str) -> str:
        if not updated and not modern:
            return value
        value = re.sub(r'''`(?:\\.|[^`\\])*`|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|[A-Za-z_$][\w$]*''', lambda m: aliases.get(stage, {}).get(m[0], m[0]), value)
        if modern:
            if stage == "primary":
                for before, after in {
                    "(0,Wz.c)(223)": "(0,Wz.c)(234)",
                    "usageItems:wt": "usageItems:kt",
                    "triggerButton:Ot": "triggerButton:Nt",
                    "children:[F,null]": "children:[j,null]",
                    "children:zt": "children:Gt",
                }.items():
                    value = value.replace(before, after)
            if stage == "thread":
                value = value.replace("children:[w,p,T,E,C,D]", "children:[T,p,E,D,w,O]")
                value = value.replace("children:[w,p,T,E,(0,oO.jsx)(CodexMuxThreadSubscription,{}),C,D]", "children:[T,p,E,D,(0,oO.jsx)(CodexMuxThreadSubscription,{}),w,O]")
            return value
        if stage == "thread":
            value = value.replace("onOpenSubagentsPanel:s}=e", "onOpenSubagentsPanel:c}=e")
            value = value.replace("children:[w,p,T,E,C,D]", "children:[T,m,E,D,w,O]")
            value = value.replace("children:[w,p,T,E,(0,cE.jsx)(CodexMuxThreadSubscription,{}),C,D]", "children:[T,m,E,D,(0,cE.jsx)(CodexMuxThreadSubscription,{}),w,O]")
        return value

    def one(pattern: str, marker: str = "") -> Path:
        marker = translate(marker)
        paths = [p for p in assets.glob(pattern) if marker in p.read_text(encoding="utf-8")]
        if len(paths) != 1:
            raise RuntimeError(f"expected one {pattern} bundle for {marker!r}, found {len(paths)}")
        return paths[0]

    def replace(text: str, old: str, new: str) -> str:
        if new.startswith(("const CODEX_MUX_API =", "const CODEX_MUX_THREAD_API =")):
            # Injected code has already had its explicit native bindings remapped.
            # Only translate the trailing native anchor, never user strings/JS keywords.
            if not new.endswith(old):
                raise RuntimeError("injected component must precede its native anchor")
            new = new[:-len(old)] + translate(old)
        else:
            new = translate(new)
        old = translate(old)
        if text.count(old) != 1:
            raise RuntimeError(f"26.903 anchor count {text.count(old)}: {old[:120]}")
        return text.replace(old, new, 1)

    def remap(text: str, names: dict[str, str]) -> str:
        # These names are renderer aliases, not user strings or account identifiers.
        for old, new in names.items():
            new = translate(new)
            text, count = re.subn(r"(?<![\w$])" + re.escape(old) + r"(?![\w$])", new, text)
            if not count:
                raise RuntimeError(f"unused 26.903 component alias: {old}")
        return text

    index = extracted / "webview" / "index.html"
    index.write_text(replace(index.read_text(encoding="utf-8"), "connect-src &#39;self&#39;",
                             f"connect-src &#39;self&#39; http://127.0.0.1:{control_port}"), encoding="utf-8")
    primary_path = one("app-primary-*.js")
    primary = primary_path.read_text(encoding="utf-8")
    component = (root / "ui" / "account-menu.js").read_text(encoding="utf-8")
    component = component.replace("__CODEX_MUX_CONTROL_PORT__", str(control_port)).replace("__CODEX_MUX_CONTROL_TOKEN__", token)
    component = remap(component, {"e7": "dq", "kXc": "Pyn", "QLs": "tG", "Lo": "fo",
                                 "Q": "HE", "BW": usage_modal_opener_alias(primary, translate("tG")), "_H": account_menu_item_alias(primary, updated, modern), "CH": "of",
                                 "jLa": "uB", "S2": "MG"})
    if modern:
        # The native menu now uses icon assets and no longer initializes the
        # legacy usage SVG. Initialize its reviewed lazy module before rendering.
        if primary.count('lR=t((()=>{i(),sR=Q(),cR=e=>') != 1:
            raise RuntimeError("expected one native usage-icon initializer")
        component = replace(component, "function CodexMuxAccountMenu() {",
                            "function CodexMuxAccountMenu() {\n  lR();")
        if primary.count('var _It,vIt,yIt,PL=t((()=>{') != 1:
            raise RuntimeError("expected one native usage-modal initializer")
        component = replace(component, "function CodexMuxUsageModal({\n  onClose,\n}) {",
                            "function CodexMuxUsageModal({\n  onClose,\n}) {\n  PL();")
    for old, new in {"list-apps": "app/list", "list-installed-apps": "app/installed",
                     "read-apps": "app/read", "list-mcp-server-status": "mcpServerStatus/list",
                     "login-mcp-server": "mcpServer/oauth/login"}.items():
        component = replace(component, f'"{old}"', f'"{new}"')
    component += "\n" + "\n".join(f"globalThis.{name}={name};" for name in (
        "codexMuxScopePluginRequest", "codexMuxProfileData", "codexMuxRateLimitResets",
        "codexMuxConsumeRateLimitReset")) + "\n"
    anchor = "function kyn(e){let t=(0,uq.c)(223),{sidebarFooter:n,triggerButton:r}=e"
    primary = replace(primary, anchor, component + anchor)
    primary = replace(primary, "usageItems:wt", "usageItems:(0,dq.jsx)(CodexMuxAccountMenu,{})")
    for old in ("sideOffset:6,triggerButton:Ot,onOpenChange:c,children:[F,null]",
                "open:s,onOpenChange:c,contentWidth:`panel`,triggerButton:Ot,children:zt"):
        primary = replace(primary, old, old.replace("onOpenChange:c", "onOpenChange:CodexMuxProfileMenuOpenChange(c)"))
    anchor = "function tG(e){let t=(0,Rdn.c)(20),{defaultResetCreditsOpen:n,initialAvailableCount:r,isRateLimitReached:i,onClose:a,onResetComplete:o}=e"
    primary = replace(primary, anchor, anchor.replace("{let t=", "{CodexMuxUseResetAccountState();let t="))
    anchor = "let v=_,y;return t[13]!==n||t[14]!==d||t[15]!==g||t[16]!==v||t[17]!==r||t[18]!==m?(y=(0,Bdn.jsx)(Adn,{defaultResetCreditsOpen:n,errorMessage:d,initialAvailableCount:r,isResetting:m,onClose:g,onResetCredit:v}),t[13]=n,t[14]=d,t[15]=g,t[16]=v,t[17]=r,t[18]=m,t[19]=y):y=t[19],y}"
    primary = replace(primary, anchor, "let v=_;return (0,Bdn.jsx)(Adn,{defaultResetCreditsOpen:n,errorMessage:d,initialAvailableCount:r,isResetting:m,onClose:g,onResetCredit:v})}")
    primary = replace(primary, "let y=v;if(g!=null){", "let y=window.__codexMuxSelectedUsageWindows??v;if(g!=null){")
    if modern:
        anchor = 'let _e=I.length===2?`h-[140px]`:`h-[70px]`,ve;'
        primary = replace(primary, anchor, 'ge=(0,ML.jsxs)(ML.Fragment,{children:[ge,window.__codexMuxResetAccountSelector??null]});' + anchor)
    else:
        anchor = "let ge;t[46]===me?ge=t[47]:(ge=(0,eG.jsxs)(Eb,{children:[me,he]}),t[46]=me,t[47]=ge);"
        primary = replace(primary, anchor, "let ge=(0,eG.jsxs)(Eb,{children:[me,he,window.__codexMuxResetAccountSelector??null]});")
    for message in ("You’re out of Codex and Work usage", "You’ve used all Codex and Work usage", "You’ve reached your usage limit"):
        primary = replace(primary, f"defaultMessage:`{message}`", "defaultMessage:`All connected subscriptions are depleted`")
    primary_path.write_text(primary, encoding="utf-8")

    stage = "initial"
    initial_path = one("app-initial-*.js")
    initial = initial_path.read_text(encoding="utf-8")
    anchor = "async sendRequest(e,t,n){if(this.dispatchMessage==null)throw Error(`AppServerRequestClient is missing a message dispatcher`);"
    initial = replace(initial, anchor, anchor.replace("{if(", "{t=globalThis.codexMuxScopePluginRequest?.(e,t)??t;if("))
    initial = replace(initial, "let e=await vO.safeGet(`/wham/profiles/me`)", "let e=await(globalThis.codexMuxProfileData?globalThis.codexMuxProfileData(globalThis.__codexMuxSelectedProfileAccountId??null):vO.safeGet(`/wham/profiles/me`))")
    query = "function x5i(){let e=(0,lq.c)(1);dz(),sb(null);let t;return e[0]===Symbol.for(`react.memo_cache_sentinel`)?(t={queryKey:[`rate-limit-reset-credits`],queryFn:C5i,select:S5i,refetchInterval:nD.ONE_MINUTE,staleTime:nD.FIVE_SECONDS},e[0]=t):t=e[0],gb(t)}"
    initial = replace(initial, query, "function x5i(){dz();sb(null);let e=window.__codexMuxResetAccountId;return gb({queryKey:[`rate-limit-reset-credits`,e??`primary`],queryFn:e?()=>globalThis.codexMuxRateLimitResets(e):C5i,select:S5i,refetchInterval:nD.ONE_MINUTE,staleTime:nD.FIVE_SECONDS})}")
    mutation = "function w5i(){let e=(0,lq.c)(3),t=fb(),n=eD(),r;return e[0]!==n||e[1]!==t?(r={mutationFn:T5i,onSuccess:(e,r)=>{let{creditId:i}=r,a=e.code;if(a===`reset`||a===`already_redeemed`){let n=e.code===`reset`?e.credit?.id??i:i;t.setQueryData([`rate-limit-reset-credits`],e=>s8i(e,a,n))}Promise.all([n([`rate-limit-status`]),n([`rate-limit-reset-credits`])])}},e[0]=n,e[1]=t,e[2]=r):r=e[2],yb(r)}"
    initial = replace(initial, mutation, "function w5i(){let e=fb(),t=eD(),n=window.__codexMuxResetAccountId,r=[`rate-limit-reset-credits`,n??`primary`];return yb({mutationFn:n?i=>globalThis.codexMuxConsumeRateLimitReset(n,i):T5i,onSuccess:(n,i)=>{let{creditId:a}=i,o=n.code;if(o===`reset`||o===`already_redeemed`){let t=o===`reset`?n.credit?.id??a:a;e.setQueryData(r,e=>s8i(e,o,t))}Promise.all([t([`rate-limit-status`]),t(r)])}})}")
    initial_path.write_text(initial, encoding="utf-8")

    stage = "profile"
    profile_path = one("profile-*.js", "className:`flex flex-col items-center`")
    profile = profile_path.read_text(encoding="utf-8")
    if modern:
        # Preserve the query object, not the destructured profile data or user ID.
        profile = replace(profile, 'O=r&&E,{data:k}=h(),', 'O=r&&E,codexMuxProfileQuery=h(),{data:k}=codexMuxProfileQuery,')
        anchor = 'let dn;t[126]!==ln||t[127]!==un?(dn=(0,$.jsx)(`section`,{"aria-busy":ln,className:`flex flex-col items-center`,children:un}),t[126]=ln,t[127]=un,t[128]=dn):dn=t[128];'
        profile = replace(profile, anchor, 'let dn=(0,$.jsx)(`section`,{"aria-busy":ln,className:`flex flex-col items-center`,children:globalThis.CodexMuxProfileAvatarStack?.({onSelect:()=>codexMuxProfileQuery.refetch()})??un});')
    else:
        anchor = 'let St;t[91]!==yt||t[92]!==xt?(St=(0,$.jsx)(`section`,{"aria-busy":yt,className:`flex flex-col items-center`,children:xt}),t[91]=yt,t[92]=xt,t[93]=St):St=t[93];'
        profile = replace(profile, anchor, anchor.replace("children:xt", "children:globalThis.CodexMuxProfileAvatarStack?.({onSelect:()=>M.refetch()})??xt"))
    profile_path.write_text(profile, encoding="utf-8")
    stage = "plugins"
    plugin_path = one("plugins-settings-*.js", "action:F,children:w})")
    plugin_path.write_text(replace(plugin_path.read_text(encoding="utf-8"), "action:F,children:w})", "action:F,children:[globalThis.CodexMuxPluginScope?.()??null,w]})"), encoding="utf-8")

    stage = "thread"
    anchor = "function iE(e){let t=(0,sE.c)(37),{onForceShow:n,isVisible:r,registerEnvironmentActionCommands:i,onOpenBackgroundAgent:a,onOpenPullRequestSidePanel:o,onOpenSubagentsPanel:s}=e"
    thread_path = one("local-conversation-thread-*.js", anchor)
    thread = thread_path.read_text(encoding="utf-8")
    component = (root / "ui" / "thread-subscription.js").read_text(encoding="utf-8")
    component = component.replace("__CODEX_MUX_CONTROL_PORT__", str(control_port)).replace("__CODEX_MUX_CONTROL_TOKEN__", token)
    component = remap(component, {"$n": "ve", "sr": "ds", "TE": "CodexMuxThreadReact", "zE": "cE", "K": "Z"})
    component = replace(component, "function CodexMuxThreadSubscription() {",
                        "function CodexMuxThreadSubscription() {\n  const CodexMuxThreadReact=De();")
    thread = replace(thread, anchor, component + "\n" + anchor)
    thread = replace(thread, "children:[w,p,T,E,C,D]", "children:[w,p,T,E,(0,cE.jsx)(CodexMuxThreadSubscription,{}),C,D]")
    thread_path.write_text(thread, encoding="utf-8")
