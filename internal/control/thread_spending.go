package control

import (
	"context"
	"net/http"
	"strings"
	"time"
)

func (s *Server) threadSpending(w http.ResponseWriter, r *http.Request) {
	if !s.authorized(r) {
		writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "unauthorized"})
		return
	}
	if r.Method != http.MethodGet {
		methodNotAllowed(w)
		return
	}
	ids := r.URL.Query()["threadId"]
	if len(ids) != 1 || ids[0] == "" || len(ids[0]) > 64 || strings.TrimSpace(ids[0]) != ids[0] || strings.ContainsRune(ids[0], 0) {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "one valid threadId is required"})
		return
	}
	ctx, cancel := context.WithTimeout(r.Context(), 20*time.Second)
	defer cancel()
	writeJSON(w, http.StatusOK, s.mux.ThreadSpending(ctx, ids[0]))
}
