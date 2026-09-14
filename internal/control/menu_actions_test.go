package control

import (
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/TheDaniXSX/codex-subscription-router-windows/internal/mux"
)

func TestMenuRenamePersistsPrimaryAndSecondaryWithoutChangingOwnership(t *testing.T) {
	server, store := newAccountActionTestServer(t)
	second, err := store.AddAccount("Second")
	if err != nil {
		t.Fatal(err)
	}
	if err := store.SetThreadOwner("task", "primary"); err != nil {
		t.Fatal(err)
	}
	for _, id := range []string{"primary", second.ID} {
		r := authorizedAccountActionRequest(http.MethodPatch, "/v1/accounts/"+id)
		r.Body = io.NopCloser(strings.NewReader(`{"label":"Personal"}`))
		w := httptest.NewRecorder()
		server.http.Handler.ServeHTTP(w, r)
		if w.Code != 200 {
			t.Fatal(w.Code, w.Body.String())
		}
		account, _ := store.Account(id)
		if account.Label != "Personal" {
			t.Fatal(account.Label)
		}
	}
	owner, _ := store.ThreadOwner("task")
	if owner != "primary" {
		t.Fatal("rename changed ownership")
	}
}

func TestMenuResetReadAndRedemptionUseOnlySelectedSyntheticAccount(t *testing.T) {
	server, store := newAccountActionTestServer(t)
	second, err := store.AddAccount("Second")
	if err != nil {
		t.Fatal(err)
	}
	// Both accounts get explicit previews so no test can reach live credentials.
	for _, id := range []string{"primary", second.ID} {
		if err := server.mux.SetResetCreditsPreview(mux.ResetCreditsPreview{AccountID: id, AvailableCount: 2}); err != nil {
			t.Fatal(err)
		}
	}
	readCount := func(id string) int {
		t.Helper()
		w := httptest.NewRecorder()
		server.http.Handler.ServeHTTP(w, authorizedAccountActionRequest("GET", "/v1/accounts/"+id+"/rate-limit-resets"))
		var result struct {
			AvailableCount int `json:"available_count"`
		}
		if w.Code != 200 || json.Unmarshal(w.Body.Bytes(), &result) != nil {
			t.Fatal(w.Code, w.Body.String())
		}
		return result.AvailableCount
	}
	if readCount(second.ID) != 2 {
		t.Fatal("missing fixture credits")
	}
	endpoint := "/v1/accounts/" + second.ID + "/rate-limit-resets/consume"
	unauthorized := httptest.NewRecorder()
	server.http.Handler.ServeHTTP(unauthorized, httptest.NewRequest("POST", endpoint, strings.NewReader(`{"creditId":"fixture-credit","redeemRequestId":"fixture-request"}`)))
	if unauthorized.Code != 401 || readCount(second.ID) != 2 {
		t.Fatal("unauthorized redemption")
	}
	r := authorizedAccountActionRequest("POST", endpoint)
	r.Body = io.NopCloser(strings.NewReader(`{"creditId":"fixture-credit","redeemRequestId":"fixture-request"}`))
	w := httptest.NewRecorder()
	server.http.Handler.ServeHTTP(w, r)
	if w.Code != 200 || !strings.Contains(w.Body.String(), `"code":"reset"`) {
		t.Fatal(w.Code, w.Body.String())
	}
	if readCount(second.ID) != 1 || readCount("primary") != 2 {
		t.Fatal("wrong subscription consumed")
	}
}
