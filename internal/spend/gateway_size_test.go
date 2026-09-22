package spend

import (
	"context"
	"crypto/sha256"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

// Reproduce the multimodal history that failed at the old 32 MiB boundary.
// Both inference and compaction must forward the complete body unchanged.
func TestGatewayLargeImageHistory(t *testing.T) {
	body := `{"model":"test","service_tier":"default","input":[{"type":"reasoning","encrypted_content":"opaque-test"},{"role":"user","content":[{"type":"input_image","image_url":"data:image/png;base64,` + strings.Repeat("AAAA", (33<<20)/4) + `"}]}]}`
	want := sha256.Sum256([]byte(body))
	for _, path := range []string{"/v1/responses", "/v1/responses/compact"} {
		t.Run(path, func(t *testing.T) {
			g, _ := gatewayFixture()
			g.Policy.Set(Mode{"second"})
			calls := 0
			g.RoundTrip = transport(func(r *http.Request) (*http.Response, error) {
				calls++
				hash := sha256.New()
				n, err := io.Copy(hash, r.Body)
				if err != nil || n != int64(len(body)) || string(hash.Sum(nil)) != string(want[:]) {
					t.Fatalf("history changed: bytes=%d want=%d err=%v", n, len(body), err)
				}
				if r.URL.Path != strings.TrimPrefix(path, "/v1") || r.Header.Get("ChatGPT-Account-ID") != "second" {
					t.Fatal("endpoint or selected identity changed")
				}
				response := "data: {\"type\":\"response.completed\"}\n\n"
				if strings.HasSuffix(path, "/compact") {
					response = `{"output":[]}`
				}
				return &http.Response{StatusCode: 200, Header: http.Header{}, Body: io.NopCloser(strings.NewReader(response))}, nil
			})
			r := httptest.NewRequest("POST", "http://localhost"+path, strings.NewReader(body))
			r.Header.Set("Authorization", "Bearer "+g.Token)
			w := httptest.NewRecorder()
			g.ServeHTTP(w, r)
			if w.Code != 200 || calls != 1 {
				t.Fatalf("status=%d upstream calls=%d", w.Code, calls)
			}
		})
	}
}

// Generate an oversized stream without storing another large buffer in the test.
type inferenceBodyReader struct {
	read int64
	err  error
}

func (r *inferenceBodyReader) Read(p []byte) (int, error) {
	if r.err != nil {
		return 0, r.err
	}
	clear(p)
	r.read += int64(len(p))
	return len(p), nil
}

func TestGatewayRequestSizeBoundBeforeSpending(t *testing.T) {
	for _, path := range []string{"/v1/responses", "/v1/responses/compact"} {
		for _, knownLength := range []bool{true, false} {
			t.Run(fmt.Sprintf("%s/known=%t", path, knownLength), func(t *testing.T) {
				g, count := gatewayFixture()
				g.Candidates = func(context.Context) ([]Candidate, error) {
					t.Fatal("oversized request reached account selection")
					return nil, nil
				}
				reader := &inferenceBodyReader{}
				r := httptest.NewRequest("POST", "http://localhost"+path, reader)
				if knownLength {
					r.ContentLength = maxInferenceRequestBytes + 1
				}
				r.Header.Set("Authorization", "Bearer "+g.Token)
				w := httptest.NewRecorder()
				g.ServeHTTP(w, r)
				if w.Code != 413 || *count != 0 || !strings.Contains(w.Body.String(), "128 MiB") {
					t.Fatalf("status=%d upstream calls=%d response=%s", w.Code, *count, w.Body.String())
				}
				wantRead := maxInferenceRequestBytes + 1
				if knownLength {
					wantRead = 0
				}
				if reader.read != wantRead {
					t.Fatalf("read %d bytes, want %d", reader.read, wantRead)
				}
			})
		}
	}
}

func TestGatewayBodyReadFailureIsNotSizeError(t *testing.T) {
	g, count := gatewayFixture()
	r := httptest.NewRequest("POST", "http://localhost/v1/responses", &inferenceBodyReader{err: io.ErrUnexpectedEOF})
	r.Header.Set("Authorization", "Bearer "+g.Token)
	w := httptest.NewRecorder()
	g.ServeHTTP(w, r)
	if w.Code != 400 || *count != 0 || !strings.Contains(w.Body.String(), "inference not sent") {
		t.Fatalf("status=%d upstream calls=%d response=%s", w.Code, *count, w.Body.String())
	}
}
