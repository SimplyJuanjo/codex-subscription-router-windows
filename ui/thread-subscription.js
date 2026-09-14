const CODEX_MUX_THREAD_API = "http://127.0.0.1:__CODEX_MUX_CONTROL_PORT__/v1";
const CODEX_MUX_THREAD_TOKEN = "__CODEX_MUX_CONTROL_TOKEN__";

function CodexMuxThreadSubscription() {
  const route = $n(sr);
  const threadId =
    route.value.routeKind === "local-thread" ? route.value.conversationId : null;
  const [spending, setSpending] = TE.useState(null);

  TE.useEffect(() => {
    let active = true;
    let generation = 0;
    let controller = null;
    setSpending(null);
    if (!threadId) {
      return () => {
        active = false;
      };
    }

    const refresh = async () => {
      const current = ++generation;
      controller?.abort();
      controller = new AbortController();
      try {
        const response = await fetch(
          `${CODEX_MUX_THREAD_API}/thread-spending?threadId=${encodeURIComponent(threadId)}`,
          {
            headers: { "X-Codex-Mux-Token": CODEX_MUX_THREAD_TOKEN },
            signal: controller.signal,
          },
        );
        if (!response.ok) throw new Error(`Request failed (${response.status})`);
        const body = await response.json();
        if (active && current === generation) {
          setSpending({ ...body, threadId });
        }
      } catch {
        if (active && current === generation) {
          setSpending((previous) => ({
            ...(previous?.threadId === threadId ? previous : {}),
            threadId,
            unavailable: true,
          }));
        }
      }
    };

    refresh();
    const subscribeEvents = globalThis.codexMuxSubscribeEvents;
    const stopEvents =
      typeof subscribeEvents === "function"
        ? subscribeEvents({
            apiBase: CODEX_MUX_THREAD_API,
            token: CODEX_MUX_THREAD_TOKEN,
            onMessage: (event) => {
              if (!active) return;
              try {
                const payload = JSON.parse(event.data);
                if (
                  payload.type === "thread-spending-updated" &&
                  payload.data?.threadId === threadId &&
                  payload.data?.accountId
                ) {
                  // Show the accepted identity immediately; quota/profile
                  // enrichment may take longer. Never reuse another account's quota.
                  setSpending({
                    threadId,
                    enabled: true,
                    request: payload.data,
                    account: {
                      id: payload.data.accountId,
                      label: payload.data.accountLabel || payload.data.accountId,
                    },
                  });
                  refresh();
                } else if (payload.type === "account-updated" ||
                           (payload.type === "inference-spent" &&
                            payload.data?.threadId === threadId)) {
                  refresh();
                }
              } catch {}
            },
          })
        : () => {};
    const warmupTimer = setTimeout(refresh, 2_000);
    const timer = setInterval(refresh, 30_000);
    return () => {
      active = false;
      controller?.abort();
      clearTimeout(warmupTimer);
      clearInterval(timer);
      stopEvents();
    };
  }, [threadId]);

  if (!threadId) return null;
  // Effects run after rendering: do not flash the previous task's identity.
  const current = spending?.threadId === threadId ? spending : null;
  const account = current?.request &&
    current.account?.id === current.request.accountId ? current.account : null;
  if (!account) {
    return (0, zE.jsx)(K.Section, {
      sectionKey: "codex-mux-subscription",
      title: "Subscription",
      children: (0, zE.jsx)("div", {
        className: "py-1 text-sm text-token-description-foreground",
        children: !current ? "Loading last request…" :
          current.unavailable || current.error ? "Last request unavailable" :
          "No routed request recorded",
      }),
    });
  }
  const weekly = codexMuxThreadWeeklyWindow(account.rateLimits);
  const remaining = weekly == null ? null : Math.max(0, 100 - weekly.usedPercent);
  const depleted = remaining === 0;
  const AccountAvatar = globalThis.CodexMuxAccountAvatar;
  return (0, zE.jsx)(K.Section, {
    sectionKey: "codex-mux-subscription",
    title: "Subscription",
    children: (0, zE.jsxs)("div", {
      className: "flex min-h-9 items-center justify-between gap-3 py-1 text-sm",
      title: current.unavailable ? "Last observed request; live updates unavailable" :
        current.error || "Subscription used by this task's latest accepted request, not its history owner or the next routing selection.",
      children: [
        (0, zE.jsxs)("div", {
          className: "flex min-w-0 items-center gap-2",
          children: [
            AccountAvatar
              ? (0, zE.jsx)(AccountAvatar, {
                  imageUrl: account.profileImageUrl,
                  label: account.label,
                  className: "size-5 shrink-0",
                })
              : null,
            (0, zE.jsxs)("div", {
              className: "min-w-0",
              children: [
                (0, zE.jsx)("div", {
                  className: "truncate text-token-text-primary",
                  children: account.planLabel
                    ? `${account.label} · ${account.planLabel}` : account.label,
                }),
                (0, zE.jsx)("div", {
                  className: "text-xs text-token-description-foreground",
                  children: current.unavailable ? "Last request · updates unavailable" : "Last request",
                }),
              ],
            }),
          ],
        }),
        (0, zE.jsx)("span", {
          className: "shrink-0 tabular-nums text-token-description-foreground",
          children:
            current.unavailable || remaining == null
              ? "Usage unavailable"
              : depleted
                ? "Depleted"
                : `${Math.round(remaining)}% remaining`,
        }),
      ],
    }),
  });
}

function codexMuxThreadWeeklyWindow(rateLimits) {
  const windows = [rateLimits?.primary, rateLimits?.secondary].filter(Boolean);
  windows.sort(
    (left, right) =>
      (left.windowDurationMins || 0) - (right.windowDurationMins || 0),
  );
  return windows.at(-1) || null;
}
