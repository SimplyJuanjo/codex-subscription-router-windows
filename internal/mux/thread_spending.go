package mux

import (
	"context"
	"time"

	"github.com/TheDaniXSX/codex-subscription-router-windows/internal/spend"
	"github.com/TheDaniXSX/codex-subscription-router-windows/internal/state"
)

type ThreadSpendingStatus struct {
	Enabled   bool               `json:"enabled"`
	Request   *state.ThreadSpend `json:"request"`
	Account   *AccountSnapshot   `json:"account"`
	Persisted bool               `json:"persisted"`
	Error     string             `json:"error,omitempty"`
}

func (m *Multiplexer) acceptThreadSpend(record spend.Record) {
	if record.Status < 200 || record.Status >= 300 || record.Outcome != "accepted" || record.ThreadID == "" || len(record.ThreadID) > 64 || record.Sequence == 0 {
		return
	}
	account, ok := m.store.Account(record.AccountID)
	if !ok {
		return
	}
	m.threadSpendMu.Lock()
	defer m.threadSpendMu.Unlock()
	if m.threadSpending == nil {
		m.threadSpending = make(map[string]state.ThreadSpend)
		m.threadSpendUnsaved = make(map[string]bool)
	}
	// Compare dispatch sequence, not response/finish time. These maps contain
	// only this process's observations: persisted sequences reset on restart.
	if previous, ok := m.threadSpending[record.ThreadID]; ok && previous.Sequence >= record.Sequence {
		return
	}
	observation := state.ThreadSpend{ThreadID: record.ThreadID, AccountID: account.ID, AccountLabel: account.Label, Sequence: record.Sequence, AcceptedAt: time.Now().UTC()}
	m.threadSpending[record.ThreadID] = observation
	// A telemetry disk failure must never reject or replay an accepted request.
	m.threadSpendUnsaved[record.ThreadID] = m.store.SaveThreadSpend(observation) != nil
	m.publish(Event{Type: "thread-spending-updated", AccountID: account.ID, Data: observation})
}

func (m *Multiplexer) ThreadSpending(ctx context.Context, threadID string) ThreadSpendingStatus {
	result := ThreadSpendingStatus{Enabled: m.requestSpending}
	m.threadSpendMu.Lock()
	if latest, ok := m.threadSpending[threadID]; ok {
		result.Request = &latest
		result.Persisted = !m.threadSpendUnsaved[threadID]
	} else {
		var err error
		result.Request, err = m.store.ThreadSpend(threadID)
		result.Persisted = err == nil && result.Request != nil
		if err != nil {
			result.Error = "Last request unavailable"
		}
	}
	m.threadSpendMu.Unlock()
	if result.Request == nil {
		return result
	}
	if !result.Persisted {
		result.Error = "Last request could not be saved for restart"
	}
	// Preserve attribution even when the account was disconnected or removed.
	account, err := m.accountSnapshotWithProfile(ctx, result.Request.AccountID, true)
	if err != nil {
		account = AccountSnapshot{ID: result.Request.AccountID, Label: result.Request.AccountLabel, Status: "unavailable"}
	}
	result.Account = &account
	return result
}
