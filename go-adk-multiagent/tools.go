package main

import (
	"fmt"

	"google.golang.org/adk/tool"
	"google.golang.org/adk/tool/functiontool"
)

type lookupInvoiceArgs struct {
	CustomerID string `json:"customer_id"`
}

type lookupInvoiceResult struct {
	CustomerID string  `json:"customer_id"`
	Amount     float64 `json:"amount"`
	Currency   string  `json:"currency"`
	Status     string  `json:"status"`
	Found      bool    `json:"found"`
}

var fakeInvoices = map[string]lookupInvoiceResult{
	"1234": {CustomerID: "1234", Amount: 199.90, Currency: "BRL", Status: "paid", Found: true},
	"5678": {CustomerID: "5678", Amount: 49.90, Currency: "BRL", Status: "open", Found: true},
}

func lookupInvoiceTool() tool.Tool {
	t, err := functiontool.New(functiontool.Config{
		Name:        "lookup_invoice",
		Description: "Look up the latest invoice for a customer by their numeric ID.",
	}, func(_ tool.Context, in lookupInvoiceArgs) (lookupInvoiceResult, error) {
		if inv, ok := fakeInvoices[in.CustomerID]; ok {
			return inv, nil
		}
		return lookupInvoiceResult{CustomerID: in.CustomerID, Found: false}, nil
	})
	if err != nil {
		panic(err)
	}
	return t
}

type checkStatusArgs struct {
	Service string `json:"service"`
}

type checkStatusResult struct {
	Service string `json:"service"`
	Status  string `json:"status"`
	Note    string `json:"note"`
}

var fakeStatus = map[string]checkStatusResult{
	"api":      {Service: "api", Status: "operational", Note: "all regions green"},
	"database": {Service: "database", Status: "degraded", Note: "elevated read latency in us-east-1"},
	"router":   {Service: "router", Status: "operational", Note: ""},
}

func checkStatusTool() tool.Tool {
	t, err := functiontool.New(functiontool.Config{
		Name:        "check_service_status",
		Description: "Check the operational status of an internal service. Valid services: api, database, router.",
	}, func(_ tool.Context, in checkStatusArgs) (checkStatusResult, error) {
		if s, ok := fakeStatus[in.Service]; ok {
			return s, nil
		}
		return checkStatusResult{Service: in.Service, Status: "unknown", Note: "service not registered"}, nil
	})
	if err != nil {
		panic(err)
	}
	return t
}

type createTicketArgs struct {
	Summary  string `json:"summary"`
	Priority string `json:"priority"`
}

type createTicketResult struct {
	TicketID string `json:"ticket_id"`
	Summary  string `json:"summary"`
	Priority string `json:"priority"`
}

var ticketCounter int

func createTicketTool() tool.Tool {
	t, err := functiontool.New(functiontool.Config{
		Name:        "create_ticket",
		Description: "Open a support ticket for a human agent. Priority must be one of: low, medium, high, urgent.",
	}, func(_ tool.Context, in createTicketArgs) (createTicketResult, error) {
		ticketCounter++
		return createTicketResult{
			TicketID: fmt.Sprintf("T-%05d", ticketCounter),
			Summary:  in.Summary,
			Priority: in.Priority,
		}, nil
	})
	if err != nil {
		panic(err)
	}
	return t
}
