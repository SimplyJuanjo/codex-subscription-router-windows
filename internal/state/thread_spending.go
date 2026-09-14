package state

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"io"
	"os"
	"path/filepath"
	"time"

	"github.com/TheDaniXSX/codex-subscription-router-windows/internal/securefs"
)

// ThreadSpend is observation, never thread ownership or a routing preference.
// One bounded sidecar per thread survives restarts without retaining prompts,
// credentials, or an unbounded request log. Older routers ignore these files.
type ThreadSpend struct {
	ThreadID     string    `json:"threadId"`
	AccountID    string    `json:"accountId"`
	AccountLabel string    `json:"accountLabel"`
	Sequence     uint64    `json:"sequence"`
	AcceptedAt   time.Time `json:"acceptedAt"`
}

func (r ThreadSpend) validate() error {
	if validateThreadID(r.ThreadID) != nil || len(r.ThreadID) > 64 || validateAccountID(r.AccountID) != nil || len(r.AccountLabel) > 256 || r.Sequence == 0 || r.AcceptedAt.IsZero() {
		return errors.New("invalid thread spending observation")
	}
	return nil
}

func (s *Store) threadSpendPath(threadID string) string {
	sum := sha256.Sum256([]byte(threadID))
	return filepath.Join(s.root, "thread-spending", hex.EncodeToString(sum[:])+".json")
}

func (s *Store) SaveThreadSpend(record ThreadSpend) error {
	if err := record.validate(); err != nil {
		return err
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	path := s.threadSpendPath(record.ThreadID)
	if err := ensureNoReparsePath(s.root, path); err != nil && !errors.Is(err, os.ErrNotExist) {
		return err
	}
	dir := filepath.Dir(path)
	if err := os.MkdirAll(dir, 0o700); err != nil {
		return err
	}
	if err := securefs.PrivateDirectory(dir); err != nil {
		return err
	}
	data, err := json.Marshal(struct {
		Version int `json:"version"`
		ThreadSpend
	}{1, record})
	if err != nil {
		return err
	}
	return atomicWriteFile(path, append(data, '\n'), 0o600)
}

func (s *Store) ThreadSpend(threadID string) (*ThreadSpend, error) {
	if validateThreadID(threadID) != nil || len(threadID) > 64 {
		return nil, errors.New("invalid thread ID")
	}
	s.mu.RLock()
	defer s.mu.RUnlock()
	path := s.threadSpendPath(threadID)
	if err := ensureNoReparsePath(s.root, path); err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return nil, nil
		}
		return nil, err
	}
	info, err := os.Lstat(path)
	if errors.Is(err, os.ErrNotExist) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	if !info.Mode().IsRegular() || info.Size() > 4096 {
		return nil, errors.New("invalid thread spending file")
	}
	if err := securefs.PrivateFile(path); err != nil {
		return nil, err
	}
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	if err := rejectDuplicateJSONKeys(data); err != nil {
		return nil, err
	}
	var input struct {
		Version int `json:"version"`
		ThreadSpend
	}
	decoder := json.NewDecoder(bytes.NewReader(data))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&input); err != nil {
		return nil, err
	}
	var trailing any
	if err := decoder.Decode(&trailing); !errors.Is(err, io.EOF) {
		return nil, errors.New("trailing thread spending data")
	}
	if input.Version != 1 || input.ThreadID != threadID {
		return nil, errors.New("invalid thread spending identity or version")
	}
	if err := input.ThreadSpend.validate(); err != nil {
		return nil, err
	}
	return &input.ThreadSpend, nil
}
