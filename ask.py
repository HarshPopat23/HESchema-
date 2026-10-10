"""Interactive local prompt testing tool for HESchema using Groq (or any configured provider)."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from heschema.domains import DOMAINS, reference_schema
from heschema.providers import Provider, ProviderError
from heschema.schema import SchemaEngine
from heschema.validation import ENVELOPE, envelope, evaluate
from heschema.benchmark import messages_for
from heschema.jsonio import loads


def display_result(prompt, domain, raw_text, parsed, validation, latency_ms):
    print("\n" + "=" * 65)
    print(f"  HESchema Local Test Result")
    print("=" * 65)
    print(f"Domain:           {domain} (tool: {DOMAINS[domain]['tool']})")
    print(f"User Prompt:      \"{prompt}\"")
    print(f"Latency:          {latency_ms:.1f} ms")
    
    status = validation.get("result", "FAIL")
    status_icon = "PASS [OK]" if status == "PASS" else "FAIL [REJECTED]"
    print(f"Validation:       {status_icon}")
    print("-" * 65)

    if parsed:
        print("Action:          ", parsed.get("action"))
        print("Tool:            ", parsed.get("tool"))
        print("Arguments:       ", json.dumps(parsed.get("arguments", {}), indent=2))
        if parsed.get("missingFields"):
            print("Missing Fields:  ", parsed.get("missingFields"))
        if parsed.get("reason"):
            print("Reason:          ", parsed.get("reason"))
    else:
        print("Raw Output:      ", raw_text)

    print("-" * 65)
    print("Detailed Checks:")
    print(f"  - Valid JSON:                {validation.get('jsonValid')}")
    print(f"  - Action Correct:            {validation.get('actionCorrect')}")
    print(f"  - Schema Valid:              {validation.get('referenceSchemaValid')}")
    print(f"  - Semantic Valid:            {validation.get('semanticValid')}")
    print(f"  - Policy Valid:              {validation.get('policyValid')}")
    print(f"  - Execution Authorized:      {validation.get('executionAuthorized')} (Always False by design)")

    errors = validation.get("errors", [])
    if errors:
        print("\nErrors / Policy Violations:")
        for idx, err in enumerate(errors, 1):
            print(f"  {idx}. {err}")
    print("=" * 65 + "\n")


async def run_prompt(prompt: str, domain: str = "flights", provider_name: str = "groq", model: str = None):
    if domain not in DOMAINS:
        print(f"Error: Unknown domain '{domain}'. Available domains: {list(DOMAINS.keys())}")
        return

    spec = DOMAINS[domain]
    ref_schema = reference_schema(domain)
    engine = SchemaEngine("jsonschema")
    case = {"domain": domain, "prompt": prompt}

    print(f"\nSending prompt to {provider_name} ({domain} domain)...")
    try:
        provider = Provider(provider_name, model=model)
    except Exception as e:
        print(f"Provider Error: {e}")
        return

    try:
        messages = messages_for(case, ref_schema)
        gen = await provider.generate(messages)
    except ProviderError as e:
        print(f"Generation failed: {e}")
        return
    finally:
        await provider.close()

    raw_text = gen.text
    parsed = None
    try:
        parsed = loads(raw_text)
    except Exception:
        pass

    extracted_args = parsed.get("arguments", {}) if parsed else {}
    action = parsed.get("action", "call_tool") if parsed else "call_tool"
    tool = parsed.get("tool", spec["tool"]) if parsed else spec["tool"]

    val = evaluate(
        raw=raw_text,
        engine=engine,
        reference_schema=ref_schema,
        candidate_schema=ref_schema,
        expected={"action": action, "tool": tool, "arguments": extracted_args},
        state=extracted_args,
        policy=spec.get("policy", {})
    )

    display_result(prompt, domain, raw_text, parsed, val, gen.latency_ms)


def main():
    parser = argparse.ArgumentParser(description="Ask HESchema with a local prompt")
    parser.add_argument("prompt", nargs="?", help="Your test prompt")
    parser.add_argument("--domain", "-d", default="flights", choices=list(DOMAINS.keys()), help="Target domain")
    parser.add_argument("--provider", "-p", default="groq", help="LLM provider (default: groq)")
    parser.add_argument("--model", "-m", help="Override provider model")
    args = parser.parse_args()

    if args.prompt:
        asyncio.run(run_prompt(args.prompt, args.domain, args.provider, args.model))
    else:
        print("=" * 65)
        print("  HESchema Interactive Prompt Tester (Groq Connected)")
        print("=" * 65)
        print(f"Available Domains: {', '.join(DOMAINS.keys())}")
        print("Type 'exit' or press Ctrl+C to quit.\n")

        while True:
            try:
                domain = input(f"Select domain [{args.domain}]: ").strip() or args.domain
                if domain.lower() in {"exit", "quit"}:
                    break
                if domain not in DOMAINS:
                    print(f"Unknown domain. Choose from: {list(DOMAINS.keys())}\n")
                    continue
                prompt = input("Enter prompt: ").strip()
                if not prompt or prompt.lower() in {"exit", "quit"}:
                    break
                asyncio.run(run_prompt(prompt, domain, args.provider, args.model))
            except (KeyboardInterrupt, EOFError):
                print("\nExiting.")
                break


if __name__ == "__main__":
    main()
