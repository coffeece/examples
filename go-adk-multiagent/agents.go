package main

import (
	"google.golang.org/adk/agent"
	"google.golang.org/adk/agent/llmagent"
	"google.golang.org/adk/model"
	"google.golang.org/adk/tool"
)

func buildCoordinator(m model.LLM) (agent.Agent, error) {
	billing, err := llmagent.New(llmagent.Config{
		Name:        "billing",
		Model:       m,
		Description: "Answers questions about invoices, payments, refunds, and billing-related issues.",
		Instruction: "You are a billing specialist. Use lookup_invoice to fetch the customer's invoice and explain its status in plain language. " +
			"If the user asks about anything outside billing, hand back to the coordinator by calling transfer_to_agent with name 'coordinator'.",
		Tools: []tool.Tool{lookupInvoiceTool()},
	})
	if err != nil {
		return nil, err
	}

	technical, err := llmagent.New(llmagent.Config{
		Name:        "technical",
		Model:       m,
		Description: "Answers technical questions about the platform's services (api, database, router).",
		Instruction: "You are a technical support specialist. Use check_service_status to look up live status. " +
			"Be concise; lead with whether the service is operational. If the question isn't technical, hand back to coordinator.",
		Tools: []tool.Tool{checkStatusTool()},
	})
	if err != nil {
		return nil, err
	}

	escalation, err := llmagent.New(llmagent.Config{
		Name:        "escalation",
		Model:       m,
		Description: "Opens a human-handoff ticket when the user is unhappy or the issue can't be resolved by other agents.",
		Instruction: "You are the escalation desk. Use create_ticket to open a ticket. " +
			"Always confirm to the user that a human will follow up and include the ticket id. Pick priority based on user tone.",
		Tools: []tool.Tool{createTicketTool()},
	})
	if err != nil {
		return nil, err
	}

	coordinator, err := llmagent.New(llmagent.Config{
		Name:        "coordinator",
		Model:       m,
		Description: "Front-line help-desk router that delegates to a specialist sub-agent.",
		Instruction: "You are a help-desk coordinator. Read the user's message and call transfer_to_agent to delegate:\n" +
			"- 'billing' for invoices, payments, refunds.\n" +
			"- 'technical' for outage, status, errors.\n" +
			"- 'escalation' when the user is angry or asks for a human.\n" +
			"Do NOT answer the user yourself unless none of the specialists fit; in that case ask one short clarifying question.",
		SubAgents: []agent.Agent{billing, technical, escalation},
	})
	if err != nil {
		return nil, err
	}
	return coordinator, nil
}
