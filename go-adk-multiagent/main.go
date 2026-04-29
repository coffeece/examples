package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/ardanlabs/conf/v3"
	"google.golang.org/adk/agent"
	"google.golang.org/adk/model/gemini"
	"google.golang.org/adk/runner"
	"google.golang.org/adk/session"
	"google.golang.org/genai"
)

type appConfig struct {
	Web struct {
		Port            int           `conf:"default:8888"`
		ShutdownTimeout time.Duration `conf:"default:10s"`
	}
	Gemini struct {
		APIKey string `conf:"mask"`
		Model  string `conf:"default:gemini-2.5-flash"`
	}
	App struct {
		Name string `conf:"default:helpdesk"`
	}
}

func main() {
	if err := run(); err != nil {
		log.Fatalf("fatal: %v", err)
	}
}

func run() error {
	var cfg appConfig
	help, err := conf.Parse("AGENT", &cfg)
	if err != nil {
		if err == conf.ErrHelpWanted {
			fmt.Println(help)
			return nil
		}
		return fmt.Errorf("parsing config: %w", err)
	}

	if strings.TrimSpace(cfg.Gemini.APIKey) == "" {
		return fmt.Errorf("AGENT_GEMINI_API_KEY is required (set via `tsuru env-set -a <app> AGENT_GEMINI_API_KEY=... --private`)")
	}

	if portEnv := os.Getenv("PORT"); portEnv != "" {
		fmt.Sscanf(portEnv, "%d", &cfg.Web.Port)
	}

	ctx := context.Background()

	llm, err := gemini.NewModel(ctx, cfg.Gemini.Model, &genai.ClientConfig{APIKey: cfg.Gemini.APIKey})
	if err != nil {
		return fmt.Errorf("creating gemini model: %w", err)
	}

	root, err := buildCoordinator(llm)
	if err != nil {
		return fmt.Errorf("building agents: %w", err)
	}

	r, err := runner.New(runner.Config{
		AppName:           cfg.App.Name,
		Agent:             root,
		SessionService:    session.InMemoryService(),
		AutoCreateSession: true,
	})
	if err != nil {
		return fmt.Errorf("creating runner: %w", err)
	}

	mux := http.NewServeMux()
	mux.HandleFunc("/healthz", func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte("ok"))
	})
	mux.HandleFunc("/chat", chatHandler(r))

	addr := fmt.Sprintf(":%d", cfg.Web.Port)
	log.Printf("agent loaded: helpdesk-coordinator with sub-agents [billing, technical, escalation]; listening on %s", addr)
	return http.ListenAndServe(addr, mux)
}

type chatRequest struct {
	SessionID string `json:"session_id"`
	UserID    string `json:"user_id"`
	Message   string `json:"message"`
}

type chatResponse struct {
	Reply string `json:"reply"`
	Agent string `json:"agent"`
}

func chatHandler(r *runner.Runner) http.HandlerFunc {
	return func(w http.ResponseWriter, req *http.Request) {
		if req.Method != http.MethodPost {
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		var body chatRequest
		if err := json.NewDecoder(req.Body).Decode(&body); err != nil {
			http.Error(w, "invalid json", http.StatusBadRequest)
			return
		}
		if strings.TrimSpace(body.Message) == "" {
			http.Error(w, "message is required", http.StatusBadRequest)
			return
		}
		if body.UserID == "" {
			body.UserID = "anon"
		}
		if body.SessionID == "" {
			body.SessionID = fmt.Sprintf("s-%d", time.Now().UnixNano())
		}

		userMsg := genai.NewContentFromText(body.Message, genai.RoleUser)

		var lastText, lastAuthor string
		for ev, err := range r.Run(req.Context(), body.UserID, body.SessionID, userMsg, agent.RunConfig{}) {
			if err != nil {
				log.Printf("runner error: %v", err)
				http.Error(w, "agent run failed", http.StatusInternalServerError)
				return
			}
			if ev == nil || !ev.IsFinalResponse() {
				continue
			}
			if ev.Content == nil {
				continue
			}
			text := joinTextParts(ev.Content)
			if text != "" {
				lastText = text
				lastAuthor = ev.Author
			}
		}

		if lastText == "" {
			lastText = "(no response generated)"
			lastAuthor = "coordinator"
		}

		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(chatResponse{Reply: lastText, Agent: lastAuthor})
	}
}

func joinTextParts(c *genai.Content) string {
	var b strings.Builder
	for _, p := range c.Parts {
		if p == nil {
			continue
		}
		if p.Text != "" {
			b.WriteString(p.Text)
		}
	}
	return b.String()
}
