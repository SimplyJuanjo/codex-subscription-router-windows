const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "thread-subscription.js"), "utf8");
const tick = () => new Promise(setImmediate);

function fixture() {
  let state = null, thread = "task", dependency, pendingEffect, cleanup, listener;
  const requests = [];
  const jsx = (type, props) => ({ type, props });
  const context = vm.createContext({
    AbortController, encodeURIComponent,
    TE: {
      useState: () => [state, value => { state = typeof value === "function" ? value(state) : value; }],
      useEffect: (effect, dependencies) => {
        if (dependencies[0] !== dependency) {
          dependency = dependencies[0]; pendingEffect = effect;
        }
      },
    },
    $n: () => ({ value: { routeKind: thread ? "local-thread" : "home", conversationId: thread } }),
    sr: {}, K: { Section: "section" }, zE: { jsx, jsxs: jsx },
    setInterval: () => 2, setTimeout: () => 1,
    clearInterval() {}, clearTimeout() {},
    codexMuxSubscribeEvents: options => { listener = options.onMessage; return () => { listener = null; }; },
    fetch: (url, options) => new Promise((resolve, reject) => requests.push({ url, options, resolve, reject })),
  });
  vm.runInContext(source, context);
  return {
    requests,
    render(nextThread = thread) {
      thread = nextThread;
      const result = context.CodexMuxThreadSubscription();
      if (pendingEffect) {
        cleanup?.(); const effect = pendingEffect; pendingEffect = null; cleanup = effect();
      }
      return result;
    },
    event(type, data) { listener?.({ data: JSON.stringify({ type, data }) }); },
    async respond(index, body) { requests[index].resolve({ ok: true, json: async () => body }); await tick(); },
    async fail(index) { requests[index].reject(new Error("offline")); await tick(); },
    close() { cleanup?.(); },
  };
}

function observation(id, label, used = 25) {
  return {
    enabled: true, persisted: true,
    request: { accountId: id, threadId: "task", sequence: 1 },
    account: { id, label, rateLimits: { secondary: { usedPercent: used, windowDurationMins: 10080 } } },
  };
}

test("subscription renders latest accepted account and updates immediately for Auto", async () => {
  const f = fixture();
  assert.match(JSON.stringify(f.render()), /Loading last request/);
  assert.match(f.requests[0].url, /\/thread-spending\?threadId=task$/);
  assert.equal(f.requests[0].options.headers["X-Codex-Mux-Token"], "__CODEX_MUX_CONTROL_TOKEN__");
  await f.respond(0, observation("second", "Subscription 2"));
  let view = JSON.stringify(f.render());
  assert.match(view, /Subscription 2/);
  assert.match(view, /Last request/);
  assert.match(view, /75% remaining/);
  assert.doesNotMatch(view, /Primary/);
  f.event("thread-spending-updated", { threadId: "other", accountId: "primary" });
  f.event("routing-mode-updated", { accountId: "primary" });
  assert.equal(f.requests.length, 1);
  f.event("thread-spending-updated", { threadId: "task", accountId: "primary", accountLabel: "Primary", sequence: 2 });
  view = JSON.stringify(f.render());
  assert.match(view, /Primary/);
  assert.doesNotMatch(view, /75% remaining|Subscription 2/);
  await f.respond(1, observation("primary", "Primary", 50));
  assert.match(JSON.stringify(f.render()), /50% remaining/);
  f.close();
});

test("stale responses and navigation cannot restore another account or task", async () => {
  const f = fixture(); f.render();
  f.event("thread-spending-updated", { threadId: "task", accountId: "second", accountLabel: "Subscription 2" });
  assert.equal(f.requests[0].options.signal.aborted, true);
  await f.respond(1, observation("second", "Subscription 2"));
  await f.respond(0, observation("primary", "Primary"));
  assert.doesNotMatch(JSON.stringify(f.render()), /Primary/);
  const firstNewRender = JSON.stringify(f.render("new-task"));
  assert.doesNotMatch(firstNewRender, /Subscription 2/);
  assert.match(firstNewRender, /Loading/);
  await f.respond(2, { enabled: true, request: null, account: null });
  assert.match(JSON.stringify(f.render()), /No routed request recorded/);
  assert.equal(f.render(null), null);
  f.close();
});

test("unavailable updates retain evidence without showing stale quota or Primary fallback", async () => {
  const f = fixture(); f.render();
  await f.fail(0);
  assert.match(JSON.stringify(f.render()), /Last request unavailable/);
  assert.doesNotMatch(JSON.stringify(f.render()), /Primary/);
  f.event("thread-spending-updated", { threadId: "task", accountId: "second", accountLabel: "Subscription 2" });
  await f.fail(1);
  const view = JSON.stringify(f.render());
  assert.match(view, /Subscription 2/);
  assert.match(view, /updates unavailable/);
  assert.doesNotMatch(view, /% remaining/);
  f.close();
});

test("UI refuses a response whose quota/account does not match the attributed request", async () => {
  const f = fixture(); f.render();
  const body = observation("second", "Subscription 2"); body.account = { id: "primary", label: "Primary" };
  await f.respond(0, body);
  assert.doesNotMatch(JSON.stringify(f.render()), /Primary/);
  f.close();
});
