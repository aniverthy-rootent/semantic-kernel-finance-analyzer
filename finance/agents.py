"""Six ChatCompletionAgents (Semantic Kernel) that call the ledger plugins via function calling."""
from __future__ import annotations

import os

from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.ai import FunctionChoiceBehavior

from .plugins import AnalyticsPlugin, BudgetPlugin, CategoryPlugin, Ledger, LedgerPlugin

COMPAT = {
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai/", "GEMINI_API_KEY"),
    "groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY"),
    "deepseek": ("https://api.deepseek.com/v1", "DEEPSEEK_API_KEY"),
    "together": ("https://api.together.xyz/v1", "TOGETHER_API_KEY"),
    "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
}


def make_service():
    """LLM_SPEC="<provider>:<model>": openai | azure | anthropic | google | ollama | mistral | bedrock | groq ..."""
    provider, _, model = os.environ.get("LLM_SPEC", "openai:gpt-4o").partition(":")
    sid = "chat"
    if provider == "openai":
        from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
        return OpenAIChatCompletion(ai_model_id=model, service_id=sid)
    if provider == "azure":
        from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
        return AzureChatCompletion(deployment_name=model, service_id=sid)
    if provider == "anthropic":
        from semantic_kernel.connectors.ai.anthropic import AnthropicChatCompletion
        return AnthropicChatCompletion(ai_model_id=model, service_id=sid)
    if provider == "google":
        from semantic_kernel.connectors.ai.google.google_ai import GoogleAIChatCompletion
        return GoogleAIChatCompletion(gemini_model_id=model, service_id=sid)
    if provider == "ollama":
        from semantic_kernel.connectors.ai.ollama import OllamaChatCompletion
        return OllamaChatCompletion(ai_model_id=model, service_id=sid)
    if provider == "mistral":
        from semantic_kernel.connectors.ai.mistral_ai import MistralAIChatCompletion
        return MistralAIChatCompletion(ai_model_id=model, service_id=sid)
    if provider == "bedrock":
        from semantic_kernel.connectors.ai.bedrock import BedrockChatCompletion
        return BedrockChatCompletion(model_id=model, service_id=sid)
    if provider in COMPAT:
        from openai import AsyncOpenAI
        from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
        base, env = COMPAT[provider]
        return OpenAIChatCompletion(ai_model_id=model, service_id=sid,
                                    async_client=AsyncOpenAI(api_key=os.environ[env], base_url=base))
    raise ValueError(f"unsupported LLM_SPEC provider: {provider}")


def build_team():
    ledger, service = Ledger(), make_service()
    auto = FunctionChoiceBehavior.Auto()

    def agent(name, instructions, plugins=()):
        return ChatCompletionAgent(service=service, name=name, instructions=instructions,
                                   plugins=list(plugins), function_choice_behavior=auto)

    return [
        agent("Ingest", "You are the Ingest Agent. Call load_statement with the CSV path you are given and report "
              "the data-quality summary (rows, date range, income, spend, duplicates, uncategorized).",
              [LedgerPlugin(ledger)]),
        agent("Categorizer", "You are the Categorizer. Call spend_by_category. Report spend per category with "
              "percentages and propose categories for the top uncategorized merchants.", [CategoryPlugin(ledger)]),
        agent("BudgetAnalyst", "You are the Budget Analyst. Call monthly_cashflow and rule_50_30_20. Explain the "
              "cash-flow trend and how the user compares to 50/30/20, with exact numbers.",
              [AnalyticsPlugin(ledger), BudgetPlugin(ledger)]),
        agent("SubscriptionHunter", "You are the Subscription Hunter. Call recurring_charges and largest_expenses. "
              "List every recurring charge with yearly cost, flag likely unused or duplicated services, and "
              "mention any unusually large one-off expense.", [AnalyticsPlugin(ledger)]),
        agent("SavingsAdvisor", "You are the Savings Advisor. From the previous agents' findings give 5 specific, "
              "ranked actions with the estimated monthly saving of each. Do not invent numbers."),
        agent("ReportWriter", "You are the Report Writer. Produce a clear Markdown personal-finance report: "
              "summary, cash flow, spending by category, subscriptions, budget check, action plan. Use only the "
              "numbers reported by the earlier agents. This is educational information, not financial advice."),
    ]
