const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const test = require("node:test");
const source = fs.readFileSync(path.join(__dirname, "account-menu.js"), "utf8");
const event = () => ({ preventDefault() { this.prevented = true; }, stopPropagation() { this.stopped = true; } });

function fixture({ failure = false, delayed = false, failRefresh = false, modalFailure = false } = {}) {
  let accounts = [
    { id: "primary", label: "Primary", enabled: true, connected: true, controller: true },
    { id: "second", label: "Subscription 2", enabled: true, connected: true },
  ];
  const values = [accounts, false, "", "", "", null, false, "second"];
  const calls = [], modals = [];
  let index = 0, finish, focus = 0;
  const jsx = (type, props, key) => ({ type, props, key });
  const nativeModal = () => {};
  const scope = {};
  const context = vm.createContext({
    AbortController, TextEncoder, TextDecoder, setTimeout, clearTimeout, setInterval, clearInterval,
    document: { querySelector: () => ({ focus() { focus++; } }) },
    window: { prompt() { throw Error("prompt() is not supported"); } },
    e7: { jsx, jsxs: jsx, Fragment: "fragment" }, _H: "menu-item", CH: { Separator: "separator" },
    Lo: () => scope, Q: {}, S2: "icon", QLs: nativeModal,
    BW: (...args) => { if (modalFailure) throw Error("unavailable"); modals.push(args); },
    kXc: {
      useState(initial) {
        const slot = index++;
        if (!(slot in values)) values[slot] = typeof initial === "function" ? initial() : initial;
        return [values[slot], value => { values[slot] = typeof value === "function" ? value(values[slot]) : value; }];
      },
      useEffect() {}, useCallback: callback => callback,
    },
    fetch: async (url, options = {}) => {
      calls.push({ url, ...options });
      if (options.method === "PATCH") {
        if (delayed) await new Promise(resolve => { finish = resolve; });
        if (failure) return { ok: false, status: 500, json: async () => ({ error: "Name was not saved" }) };
        const id = url.split("/").at(-1), label = JSON.parse(options.body).label;
        accounts = accounts.map(a => a.id === id ? { ...a, label } : a);
        return { ok: true, json: async () => ({ account: accounts.find(a => a.id === id) }) };
      }
      assert.ok(url.endsWith("/accounts"), "only fixture account endpoints allowed");
      if (failRefresh) throw Error("Quota refresh unavailable");
      return { ok: true, json: async () => ({ accounts }) };
    },
  });
  vm.runInContext(source, context);
  function render() { index = 0; return context.CodexMuxAccountMenu().props.children; }
  const find = action => render().find(row => row.props["data-codex-mux-action"] === action);
  return { context, calls, modals, values, scope, nativeModal, render, find, release: () => finish(),
    focus: () => focus, type: label => find("rename-form").props.children[1].props.onChange({ target: { value: label } }),
  };
}

test("Rename click opens an in-menu editor and Save commits the selected subscription", async () => {
  const f = fixture(); const click = event();
  f.find("rename").props.onSelect(click);
  assert.equal(click.prevented, true);
  assert.equal(f.calls.length, 0);
  assert.equal(f.find("rename-form").props.children[1].props.value, "Subscription 2");
  f.type("  Personal  ");
  await f.find("rename-form").props.onSubmit(event());
  assert.equal(f.find("rename-form"), undefined);
  assert.equal(f.calls[0].method, "PATCH");
  assert.match(f.calls[0].url, /\/accounts\/second$/);
  assert.equal(f.calls[0].headers["X-Codex-Mux-Token"], "__CODEX_MUX_CONTROL_TOKEN__");
  assert.deepEqual(JSON.parse(f.calls[0].body), { label: "Personal" });
  assert.equal(f.values[0].find(a => a.id === "primary").label, "Primary");
  assert.equal(f.values[0].find(a => a.id === "second").label, "Personal");
  assert.ok(f.focus() > 0);
});

test("Rename supports Primary and cancellation, validation and keyboard containment", async () => {
  const f = fixture(); f.values[7] = "primary";
  f.find("rename").props.onSelect(event());
  const key = { ...event(), key: "a" };
  f.find("rename-form").props.onKeyDown(key);
  assert.equal(key.stopped, true); assert.equal(key.prevented, undefined);
  for (const label of ["   ", "x".repeat(81)]) {
    f.type(label); await f.find("rename-form").props.onSubmit(event());
    assert.equal(f.calls.length, 0); assert.ok(f.values[3]);
  }
  f.type("Main"); await f.find("rename-form").props.onSubmit(event());
  assert.match(f.calls[0].url, /\/accounts\/primary$/);
  f.find("rename").props.onSelect(event());
  const escape = { ...event(), key: "Escape" };
  f.find("rename-form").props.onKeyDown(escape);
  assert.equal(escape.prevented, true); assert.equal(f.find("rename-form"), undefined);
  f.find("rename").props.onSelect(event());
  f.find("rename-form").props.children[2].props.children[0].props.onClick();
  assert.equal(f.find("rename-form"), undefined);
});

test("Rename failures retain the draft and a duplicate submit never sends two mutations", async () => {
  const f = fixture({ failure: true, delayed: true });
  f.find("rename").props.onSelect(event()); f.type("Keep this draft");
  const form = f.find("rename-form");
  const first = form.props.onSubmit(event());
  const second = form.props.onSubmit(event()); // same render, before React updates busy
  assert.equal(f.calls.length, 1);
  assert.equal(f.find("rename-form").props.children[1].props.disabled, true);
  f.release(); await Promise.all([first, second]);
  assert.match(f.values[3], /Name was not saved/);
  assert.equal(f.find("rename-form").props.children[1].props.value, "Keep this draft");
  assert.equal(f.values[0][1].label, "Subscription 2");
});

test("A committed rename remains visible if the following quota refresh fails", async () => {
  const f = fixture({ failRefresh: true });
  f.find("rename").props.onSelect(event()); f.type("Saved");
  await f.find("rename-form").props.onSubmit(event());
  assert.equal(f.values[0][1].label, "Saved");
  assert.equal(f.find("rename-form"), undefined);
});

test("Usage click opens the reset modal without consuming a reset", () => {
  const f = fixture(); f.find("usage").props.onSelect(event());
  assert.equal(f.modals.length, 1);
  const [scope, modal] = f.modals[0];
  assert.equal(scope, f.scope);
  const close = () => {};
  const view = modal({ onClose: close });
  assert.equal(view.type, f.nativeModal);
  assert.equal(view.props.defaultResetCreditsOpen, true);
  assert.equal(view.props.onClose, close);
  assert.equal(f.calls.length, 0, "opening does not redeem credits");
});

test("Usage opener errors stay visible in the menu", () => {
  const f = fixture({ modalFailure: true }); const click = event();
  f.find("usage").props.onSelect(click);
  assert.equal(click.prevented, true);
  assert.match(f.values[3], /Usage could not be opened/);
});

test("Reset selector reads both accounts and refreshes counts after a simulated redemption", async () => {
  const f = fixture();
  const accounts = f.values[0];
  const state = [], effects = [];
  let index = 0, available = 2, redemptions = 0;
  f.context.__codexMuxConnectedAccounts = accounts;
  f.context.kXc.useState = initial => {
    const slot = index++;
    if (!(slot in state)) state[slot] = typeof initial === "function" ? initial() : initial;
    return [state[slot], value => { state[slot] = typeof value === "function" ? value(state[slot]) : value; }];
  };
  f.context.kXc.useEffect = effect => effects.push(effect);
  f.context.fetch = async (url, options = {}) => {
    assert.ok(options.headers["X-Codex-Mux-Token"]);
    let body;
    if (url.endsWith("/accounts")) body = { accounts };
    else if (url.endsWith("/accounts/second/rate-limit-resets/consume")) {
      assert.equal(options.method, "POST"); redemptions++; available--;
      body = { code: "reset", credit: { id: "synthetic" } };
    } else {
      assert.match(url, /\/accounts\/(primary|second)\/rate-limit-resets$/);
      body = { available_count: url.includes("/second/") ? available : 0, credits: [] };
    }
    return { ok: true, json: async () => body };
  };
  const render = () => { index = 0; f.context.CodexMuxUseResetAccountState(); return f.context.window.__codexMuxResetAccountSelector.props; };
  render();
  const cleanup = effects[0]();
  await new Promise(setImmediate);
  let selector = render();
  assert.equal(selector.resetCounts.primary, 0);
  assert.equal(selector.resetCounts.second, 2);
  assert.equal(redemptions, 0);
  selector.onSelect("second");
  assert.equal(render().selectedId, "second");
  assert.equal(f.context.window.__codexMuxResetAccountId, "second");
  await f.context.codexMuxConsumeRateLimitReset("second", { creditId: "synthetic", redeemRequestId: "synthetic-request" });
  await new Promise(setImmediate);
  assert.equal(render().resetCounts.second, 1);
  assert.equal(redemptions, 1);
  cleanup();
  assert.equal(f.context.__codexMuxRefreshResetAccounts, undefined);
});
