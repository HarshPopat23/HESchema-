# Executive Summary: Comparing Plain JSON Schema to HESchema Contracts

### What Was Tested?
We tested AI models on 100 real-world data tasks (like copying earthquake locations, calculating total file sizes, counting bicycle stations, and listing book authors).

We tested two different ways to guide the AI:
1. **Method A (Plain Schema):** We gave the AI a normal JSON schema and asked it to follow instructions written in plain English.
2. **Method B (HESchema Contract):** We gave the AI a contract that connects directly to verified data facts and checks math and relationships automatically.

---

### What Did We Find?

1. **How Often Did the AI Get the Right Answer?**
   - On the first try:
     - Plain Schema: **89.78%**
     - HESchema Contract: **87.44%**
   - After one chance to fix mistakes:
     - Plain Schema: **91.22%**
     - HESchema Contract: **88.33%**

2. **Catching Bad Answers (Safety):**
   - When Plain Schema was used, the validator mistakenly accepted bad answers **6.89%** of the time because standard JSON Schema doesn't check math or relationships between fields.
   - HESchema Contract caught those errors, dropping false acceptance to **0.0%**.

3. **The Cost and Speed Tradeoff:**
   - HESchema contracts include extra rules in the prompt. This used about **48.0% more tokens**.
   - Because the contracts do extra checks and have slightly longer prompts, they took about **430.0 milliseconds longer** per question.

---

### Bottom Line
HESchema contracts act like a strict proofreader. They stop the AI from making unnoticed arithmetic and copying mistakes, but they require a little more text in the prompt.
