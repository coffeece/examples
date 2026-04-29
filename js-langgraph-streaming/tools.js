import { tool } from "@langchain/core/tools";
import { TavilySearchResults } from "@langchain/community/tools/tavily_search";
import { evaluate } from "mathjs";
import { z } from "zod";

export const calculator = tool(
  ({ expression }) => {
    try {
      const result = evaluate(expression);
      return String(result);
    } catch (err) {
      return `error: ${err.message}`;
    }
  },
  {
    name: "calculator",
    description:
      "Evaluate an arithmetic expression. Use for any math the user asks about. " +
      "Examples: '17 * 19', '(1+2)*3', 'sqrt(2)'.",
    schema: z.object({ expression: z.string().describe("A mathjs-compatible expression") }),
  }
);

export function buildTools() {
  const tools = [calculator];
  if (process.env.TAVILY_API_KEY) {
    tools.push(
      new TavilySearchResults({ apiKey: process.env.TAVILY_API_KEY, maxResults: 3 })
    );
  } else {
    console.warn("TAVILY_API_KEY not set — web search disabled");
  }
  return tools;
}
