package spend

import (
	"context"
	"errors"
	"io"
	"net/http"
	"strings"
	"testing"
)

type acceptanceReader struct {
	t        *testing.T
	accepted *bool
	body     io.Reader
}

func (r acceptanceReader) Read(p []byte) (int, error) {
	if !*r.accepted {
		r.t.Fatal("body read before acceptance notification")
	}
	return r.body.Read(p)
}

func TestGatewayAcceptanceIsImmediateAndTerminalObservationIsSeparate(t *testing.T) {
	g, _ := gatewayFixture()
	accepted, finished := false, false
	g.Accepted = func(r Record) {
		if accepted || finished || r.Outcome != "accepted" || r.Status != 200 || r.ThreadID != "task" || r.AccountID != "second" || !r.Subagent {
			t.Fatal(r)
		}
		accepted = true
	}
	g.Observe = func(r Record) {
		if !accepted || r.Outcome != "completed" {
			t.Fatal(r)
		}
		finished = true
	}
	g.Policy.Set(Mode{AccountID: "second"})
	g.RoundTrip = transport(func(*http.Request) (*http.Response, error) {
		return &http.Response{StatusCode: 200, Header: http.Header{}, Body: io.NopCloser(acceptanceReader{t, &accepted, strings.NewReader("data: {\"type\":\"response.completed\"}\n\n")})}, nil
	})
	perform(g, `{"input":[],"client_metadata":{"thread_id":"task","turn_id":"turn","x-openai-subagent":"worker"}}`)
	if !accepted || !finished {
		t.Fatal("missing observations")
	}
}

func TestGatewayDoesNotAttributeRejectedUnsentOrUncertainRequests(t *testing.T) {
	for _, kind := range []string{"rejected", "credentials", "transport"} {
		t.Run(kind, func(t *testing.T) {
			g, _ := gatewayFixture()
			g.Accepted = func(Record) { t.Fatal("unconfirmed spending attributed") }
			switch kind {
			case "credentials":
				g.Credentials = func(context.Context, string) (Credentials, error) { return Credentials{}, errors.New("unavailable") }
			case "transport":
				g.RoundTrip = transport(func(*http.Request) (*http.Response, error) { return nil, io.ErrUnexpectedEOF })
			case "rejected":
				g.RoundTrip = transport(func(*http.Request) (*http.Response, error) {
					return &http.Response{StatusCode: 429, Body: io.NopCloser(strings.NewReader("rejected"))}, nil
				})
			}
			perform(g, `{"input":[],"client_metadata":{"thread_id":"task"}}`)
		})
	}
}
