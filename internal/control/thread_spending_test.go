package control

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/TheDaniXSX/codex-subscription-router-windows/internal/mux"
	"github.com/TheDaniXSX/codex-subscription-router-windows/internal/state"
)

func TestThreadSpendingEndpointIsAuthenticatedReadOnlyAndIndependentOfOwner(t *testing.T) {
	s, store := newAccountActionTestServer(t)
	for _, tc := range []struct {
		method, path string
		auth         bool
		want         int
	}{
		{"GET", "/v1/thread-spending?threadId=task", false, 401},
		{"POST", "/v1/thread-spending?threadId=task", true, 405},
		{"GET", "/v1/thread-spending", true, 400},
		{"GET", "/v1/thread-spending?threadId=a&threadId=b", true, 400},
		{"GET", "/v1/thread-spending?threadId=%00", true, 400},
		{"GET", "/v1/thread-spending?threadId=task", true, 200},
	} {
		r := httptest.NewRequest(tc.method, tc.path, nil)
		if tc.auth {
			r = authorizedAccountActionRequest(tc.method, tc.path)
		}
		w := httptest.NewRecorder()
		s.http.Handler.ServeHTTP(w, r)
		if w.Code != tc.want {
			t.Fatalf("%s: got %d want %d", tc.path, w.Code, tc.want)
		}
	}
	second, err := store.AddAccount("Second")
	if err != nil {
		t.Fatal(err)
	}
	if err := store.SetThreadOwner("task", "primary"); err != nil {
		t.Fatal(err)
	}
	if err := store.SaveThreadSpend(state.ThreadSpend{ThreadID: "task", AccountID: second.ID, AccountLabel: second.Label, Sequence: 1, AcceptedAt: time.Now().UTC()}); err != nil {
		t.Fatal(err)
	}
	w := httptest.NewRecorder()
	s.http.Handler.ServeHTTP(w, authorizedAccountActionRequest(http.MethodGet, "/v1/thread-spending?threadId=task"))
	var got mux.ThreadSpendingStatus
	if err := json.Unmarshal(w.Body.Bytes(), &got); err != nil {
		t.Fatal(err)
	}
	if got.Account == nil || got.Account.ID != second.ID || got.Request == nil || !got.Persisted {
		t.Fatal(got)
	}
}
