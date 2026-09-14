package state

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestThreadSpendingSidecarRoundTripAndIsolation(t *testing.T) {
	root := t.TempDir()
	s, err := Open(filepath.Join(root, "state"), filepath.Join(root, "primary"))
	if err != nil {
		t.Fatal(err)
	}
	r := ThreadSpend{ThreadID: "task", AccountID: "primary", AccountLabel: "Primary", Sequence: 123, AcceptedAt: time.Now().UTC()}
	if err := s.SaveThreadSpend(r); err != nil {
		t.Fatal(err)
	}
	got, err := s.ThreadSpend("task")
	if err != nil || *got != r {
		t.Fatal(got, err)
	}
	if got, err := s.ThreadSpend("other-task"); err != nil || got != nil {
		t.Fatal(got, err)
	}
	if _, ok := s.ThreadOwner("task"); ok {
		t.Fatal("observation changed ownership")
	}
	r.ThreadID = "../safe-hashed-name"
	if err := s.SaveThreadSpend(r); err != nil {
		t.Fatal(err)
	}
	if filepath.Dir(s.threadSpendPath(r.ThreadID)) != filepath.Join(s.Root(), "thread-spending") {
		t.Fatal("unsafe path")
	}
}

func TestThreadSpendingRejectsMalformedSidecars(t *testing.T) {
	root := t.TempDir()
	s, err := Open(filepath.Join(root, "state"), filepath.Join(root, "primary"))
	if err != nil {
		t.Fatal(err)
	}
	r := ThreadSpend{ThreadID: "task", AccountID: "primary", AccountLabel: "Primary", Sequence: 1, AcceptedAt: time.Now().UTC()}
	if err := s.SaveThreadSpend(r); err != nil {
		t.Fatal(err)
	}
	valid, err := os.ReadFile(s.threadSpendPath("task"))
	if err != nil {
		t.Fatal(err)
	}
	for _, body := range []string{
		strings.Replace(string(valid), `"version":1`, `"version":2`, 1),
		strings.Replace(string(valid), `"version":1`, `"version":1,"version":1`, 1),
		strings.Replace(string(valid), `"threadId":"task"`, `"threadId":"different"`, 1),
		strings.Replace(string(valid), `"version":1`, `"unexpected":true,"version":1`, 1),
		string(valid) + "{}", strings.Repeat("x", 4097),
	} {
		if err := os.WriteFile(s.threadSpendPath("task"), []byte(body), 0o600); err != nil {
			t.Fatal(err)
		}
		if _, err := s.ThreadSpend("task"); err == nil {
			t.Fatal("accepted invalid sidecar")
		}
	}
}
