# Auto Quant Research as a Co-Scientist — Design Notes from the OpenPhil Discussion

Auto Quant Research is, at heart, a **co-scientist agent** for finance microstructure: a system that takes a research paper as input and partners with a human researcher to produce a verified replication, a written narrative of the result, and a growing body of cross-linked findings. The "co-" matters; the system is not designed to replace the researcher, it is designed to operate as a junior colleague who can run experiments tirelessly while the senior researcher steers and signs off. The Decision Layer / Execution Layer split that runs through the rest of this repository is precisely the contract that makes the partnership work: the human is the principal investigator, the agent is the postdoc that never sleeps, and both are bound by an explicit interface.

The framing of building "co-scientist agents" comes from a separate thread of work in the AI-for-science community. The notes below are a distilled set of design ideas from the `openphil-core` Slack channel (a FLAIR / Oxford collaboration explicitly framed as "Building the Co-Scientist Agent", February–March 2026). The original conversation is freeform; this document refines the actionable points and maps each one to its implication for Auto Quant Research.

The contributors quoted here are working researchers in AI for science, alignment, and physics; their day-to-day debate about how to scaffold an AI agent for hard scientific problems aligns surprisingly closely with what Auto Quant Research has been converging on. Treat this document as a cross-validation: when an idea independently appears in two unrelated communities (general AI-for-science co-scientist design, and finance-microstructure replication via Auto Quant Research), it is more likely to be load-bearing than fashionable.

---

## 1. Scaffold construction is part of the task, not abstracted away

**Jakob (paraphrased)**: "We keep looking for a hard problem since models are too capable. But constructing the evals seems too challenging. If that's so, we should turn the task of constructing the evals into part of the problem. Make the human-AI scaffold design part of the task."

**Alex Goldie (paraphrased)**: "I think we were thinking too granularly. The task shouldn't be 'speed up this codebase'. It should just be 'solve the 3-body problem', and it comes to the human-AI system to figure out how to do so, including, e.g., speed up XYZ codebase. We were trying too hard to abstract away some of what experts should be doing with the agent. The high-level goal is the task, and the smaller steps are part of the point of the study, that an AI alone would try to solve it, whereas a human may first focus on speeding up a codebase, then running an experiment, etc."

**What this means for Auto Quant Research**: Do not give the system the instruction "run an OLS regression of log-delay on log-depth on the Dugast 2026 specification". Give it "replicate the empirical claim of Dugast, Marta, Riva (2026)" and let the Execution Layer pick the regression family, the controls, the standard-error correction, and the robustness checks. The act of decomposing the paper into a runnable spec is itself part of the work being measured. This is why the Automation Pipeline diagram shows "Paper Ingestion" as the first stage, not "Regression Spec" as the first stage; the spec is what the agent produces from the paper, not what the human dictates to the agent.

A related implication: a future evaluation of Auto Quant Research should not score how well the system runs a fixed regression. It should score how well the system, given only a paper, decomposes the claim into runnable empirical work. The decomposition quality is the capability under test.

## 2. The Darwin-Gödel pattern with humans in the loop

**Jakob**: "It's like [Sakana's Darwin Gödel Machine] but with humans in the loop." (Sakana AI's DGM is an AI that improves itself by rewriting its own code; <https://sakana.ai/dgm/>.)

**What this means for Auto Quant Research**: The system's own scaffold (its skills, its hooks, its CLAUDE.md rules) is not frozen. Each replication exposes patterns that get distilled back into new skills, hooks, or CLAUDE.md rules. The Decision Layer's signoff is the human-in-the-loop checkpoint that lets self-modification happen safely: the agent proposes a new rule or skill, the human approves it, and the next replication runs with an enriched scaffold. Over many replications, the scaffold itself is a coevolving artifact; that is exactly the DGM pattern, with the safety filter installed on each iteration.

Concretely, every time an agent skill saved time on a replication, the lesson was added to the skills folder; every time a failure mode appeared, a new hook or CLAUDE.md rule was added. The skills published in `context-engineering/skills/` are not a fixed library; they are the survivors of many small Darwin-Gödel iterations.

## 3. The AI Grant Funding model

**Yulin Wang (paraphrased)**: "Mimic the actual scientific research ecosystem: an 'AI Grant Funding' model. Multiple LLMs write research proposals, including detailing task division and human-AI collaboration plans. Human experts act as reviewers allocating compute and funding. We can iterate this: LLMs report progress, humans evaluate, and dynamically cut resources for unpromising paths."

**What this means for Auto Quant Research**: This is essentially the Decision Layer's job description, articulated more sharply than the current website does. The user is not approving a single output; the user is acting as a review committee allocating GPU-hours, attention, and human review time across competing replications. A Notion sub-page per replication is the proposal; the user's signoff or edit is the funding decision; the eventual Overleaf push is the published paper that justifies the next round of funding. This framing also makes it natural to kill replications mid-flight when their progress reports look weak, the analog of a grant being cut.

A practical addition that this framing motivates: each replication, when it pushes its raw results to Notion, should include a one-paragraph self-assessment of whether the result is worth the next stage of human review time. The Decision Layer can then triage at the page level rather than by reading every output equally.

## 4. The split between LLM strengths and human strengths

**Yulin Wang (paraphrased)**: "From my experience with models like Gemini-deep-think and GPT-5.2-pro: it seems like the LLM's greatest value lies in broad information retrieval, proposing diverse solutions, and engineering and coding. However, they can be gullible (e.g., blindly trusting stories in low-quality papers). Personally, I think the human's unique advantage is solving 'the arbitrarily complex evaluation' problem: judging quality and correctness and using tailored natural language to steer the LLMs back on track."

**What this means for Auto Quant Research**: This is the cleanest articulation seen in this thread of why the Decision Layer cannot be replaced by a smarter LLM. LLMs are good at *generation* (retrieval, breadth, code) and bad at *evaluation in the open* (when there is no clean checkable answer). Replication of a finance microstructure paper is precisely a domain where evaluation is open-ended: was the agent's interpretation of the paper's claim faithful? Did the chosen ticker subset bias the result? Is the directional consistency with the paper's number a real validation or an artifact of the modern dataset? Each of these requires the human's "arbitrarily complex evaluation" capability. The Wiki section of the website is a direct response to this insight: the Wiki exists so that the human can actually do that evaluation, by having a comprehensible reading surface for what the agent did.

The website's framing of the Wiki as a "comprehension scaffold for HITL" is the same thesis as Yulin's split, written in different words.

## 5. Coevolutionary scaffolds and meta-game design

**Jakob**: "Basically we'll design the meta-game: a coevolutionary system that gives tokens and GPU access to teams that compete for prize money. So it's Kaggle-like but the caveat is that a lot of the core logic will be built by the teams themselves. The human-AI team will be allowed to change its own scaffold as appropriate."

**What this means for Auto Quant Research**: Today there is one Auto Quant Research scaffold. Tomorrow, in the limit, there could be multiple competing scaffolds, each replicating the same paper and producing slightly different replications, with the Decision Layer choosing among them. This is structurally identical to the Kaggle-with-self-built-logic idea, applied to scientific replication instead of leaderboard tasks. Even if Auto Quant Research never literally hosts a competition, the design discipline is useful: every component of the scaffold should be modular enough that a competing version of it could be plugged in. The skills folder is already on this trajectory; CLAUDE.md is harder, since it currently encodes one user's preferences.

## 6. Proxy benchmarks: orchestrator-as-scaffold-designer

**Jakob (paraphrased)**: "I am thinking of proxy-settings for human-in-the-loop benchmarking: one of them could be scaffolding a set of different LLMs with very diverse properties together. And some of these could have human-like properties (i.e., very general but making them artificially slow). And then we'd evaluate how capable an orchestrator agent is at figuring out which agent is good for what and how to optimally scaffold them for a given task in terms of different metrics."

**What this means for Auto Quant Research**: The current Pipeline diagram shows N parallel subagents, all of which are large language models. A more rigorous version of the same idea would use heterogeneous agents: a fast-but-shallow agent for code generation, a slower-but-careful agent for spec extraction from the paper, a very slow but accurate agent (the human or a slow proxy) for the Decision Layer signoff. The orchestrator's job is then to route work to the right agent given task properties. This is a generalization of "fan-out to identical agents" into "fan-out to typed agents". Auto Quant Research could pilot this with two tiers (Sonnet for routine work, Opus for sensitive design decisions, human for final signoff) and measure whether routing accuracy improves.

## 7. Cross-domain transfer of the next-state-prediction simulator

**Kang Li (paraphrased)**: "Some info for AI for fusion: simulators are TORAX and DESC (MHD: magneto-hydro-dynamics; compressible, viscous, magnetized fluid). Datasets and benchmark: TokaMark (arXiv 2602.10132), FAIR-MAST. Optimization with constraints (where EGGRoll can be applied): stellarator optimization with constraints. People also do next-state prediction to provide a simulator for testing the control policies, which may be quite similar to the quant next-state prediction problem."

**What this means for Auto Quant Research**: The World Model in Auto Quant Research is a learned next-state predictor for limit-order-book event streams. The same machinery, conditional autoregressive density estimation, transfers to plasma state evolution in fusion control. The implication for the design of Auto Quant Research is conservative: keep the World Model interface clean enough that a different domain's simulator (a fusion next-state predictor, a weather model, a robotics dynamics model) could be slotted in without changing the surrounding Pipeline. This pushes against any temptation to bake LOB-specific assumptions into the World Model API.

A second-order implication: if the World Model can be retargeted to another scientific domain, then Auto Quant Research can also be retargeted to that domain by swapping the paper-replication templates. The pipeline is finance-microstructure-shaped today, but the shape is mostly cosmetic; the deeper architecture is "paper plus simulator equals replication," and that pattern is much broader than finance.

---

## How to read this document going forward

These insights came from open discussion; not all of them are operationalized yet in Auto Quant Research. They are recorded here so that, when a design question comes up ("should we add agent typing?", "should the system kill its own replications?", "should we bake in domain assumptions?"), there is an explicit reference to revisit. The principle is to write down the rationale at the moment it becomes available, not to wait until the design choice is forced.

Comments and additions from other contributors are welcome on the Notion mirror of this page. To add a new insight, follow the convention used here: a one-line attribution, a paraphrased quote, and a paragraph mapping the idea onto its implication for Auto Quant Research.

---

*Source thread: `openphil-core` Slack channel, FLAIR collaboration, Feb–Mar 2026.*
*Contributors quoted (alphabetical): Alex Goldie, Jakob Foerster (?), Kang Li, Yulin Wang. Channel members: Antonio León Villares, Christian Catalini (linked, not quoted), Elif Akata, Kristen Menou, Lucas Futingchen, Mohamad Ali-Dib, Tingchen Fu, Xinge Liu, Yuhe Gao.*
