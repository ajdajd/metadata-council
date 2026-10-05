# System Design: Council-Based Optimization for Data Snapshot Metadata Extraction 

# Purpose and scope 

The current metadata extraction pipeline uses a single multimodal model with Data Snapshot Metadata Schema v1.4 and a manually developed extraction prompt. We now have 102 human-validated metadata annotations that can be used to systematically improve the extraction system. 

The proposed approach uses a heterogeneous multi-model council to iteratively develop **the extraction policy (i.e., prompts \+ extraction rules)**. 

The council is a development mechanism, not the intended production extractor. Its role is to use qualitative deliberation to propose, critique, and refine the extraction policy aided by human-labeled examples and empirical results from each round. 

## Future work 

A later phase may involve hardening and formalizing metrics based on recurring failure modes and other findings. 

A much later phase may use the resulting high-quality annotations to fine-tune a smaller task-specific multimodal model, but this is outside the current scope. 

# Data and experimental split 

Available inputs: 

* 3,900+ data snapshots   
* 102 Data Snapshots with human-validated metadata   
* Data Snapshot Metadata Schema v1.4 

   
The proposed split for the 102 human-validated snapshots is: 

| Split  | Total  | Per stratum  | Purpose  |
| ----- | :---: | :---: | ----- |
| Discovery  | 66  | 11  | Used by the council to learn rules and inspect edge cases  |
| Hold-out  | 36  | 6  | Reserved for later formal evaluation    |

The remaining unlabeled snapshots will be used as challenge samples to expose new edge cases. 

# Phase 1: Optimize extraction policy 

## Artifacts 

Canonical artifacts (carried forward across rounds): 

1. **Extraction Policy** (`001_policy.md`) — the current canonical prompt and extraction rules to be used by the reference extractor.   
2. **Cumulative Experiment State** (`001_experiment_state.md`) — a compact synthesis of everything that should carry forward across rounds: accepted rules, known failure modes, prior decisions, rejected ideas and why, open challenges, and other durable findings.   
3. **Extraction Results** (`001_extractions.jsonl`) — outputs produced using the current extraction policy by the reference extractor on the samples selected for that round. 

Audit/debug artifacts: 

4. **Round Findings** (`001_round_findings.md`) — key observations from the round, including failure modes, rationale for policy changes, gold/schema challenges, rejected proposals, and unresolved disagreements.   
5. **Council Deliberation Record** (`001_deliberation.md`) — the full audit trail containing Proposal A/B/C, cross-critiques, revised proposals, and the orchestrator synthesis. This is retained for reproducibility.   
6. **Round Manifest** (`001_manifest.json`) — machine-readable metadata for reproducibility, including sample IDs, model configuration, round index, timestamps, and other run settings.   
7. **Human Review** (`001_human_review.md`) — any interventions made after the round, such as approved gold corrections, accepted schema changes, or adjustments to experiment state before the next round. This file may not exist when no intervention is needed. 

## Components 

1. **Council members.** A small set of heterogeneous multimodal models that will independently analyze the inputs (canonical artifacts) and generate their own proposals.
    * A proposal may contain observations, evidence-backed policy changes, gold/schema challenges, and other issues that should be carried forward.   
2. **Orchestrator.** A separate high-capability model that will synthesize council deliberation into the updated Extraction Policy, Cumulative Experiment State, and Round Findings.   
3. **Reference extractor.** A fixed multimodal model that will execute the current extraction policy.   
    * Keeping this model fixed helps isolate the effects of policy changes from changes in the underlying model.   
4. **Experiment controller.** A Python-based controller that will manage sampling, model calls, artifact versioning, and experiment logging.   
    * Agent frameworks such as Pi may be used for council communication, but the outer experiment remains explicitly controlled. 

## Council deliberation round 

For each deliberation round, the council members receive: 

* Previous iteration’s extraction results
	* Human-labeled Data Snapshots   
        * Generated metadata from the current extraction policy   
        * Human annotation   
    * Unlabeled Data Snapshots   
        * Generated metadata from the current extraction policy   
* The current Extraction Policy   
* The Cumulative Experiment State 

The council interaction for each round will be as follows: 

1. Council members will receive the inputs and generate independent proposals. In particular, they...   
	* Will qualitatively review extraction results    
	* May flag questionable gold annotations or possible schema limitations.    
        * These will be treated as proposals only. Gold labels and the schema are changed only after human review.   
2. Council members will cross-critique the proposals.   
3. Council members will revise their work.   
4. The orchestrator will synthesize the proposals to write the updated extraction policy and other artifacts. 

```
                         Round inputs
                              │
             ┌────────────────┼────────────────┐
             ↓                ↓                ↓
        Councilor A      Councilor B      Councilor C
             │                │                │
             ↓                ↓                ↓
        Proposal A       Proposal B       Proposal C
             │                │                │
             └────────────────┼────────────────┘
                              ↓
                     Cross-critique round
              A critiques B/C; B critiques A/C;
                       C critiques A/B
                              │
             ┌────────────────┼────────────────┐
             ↓                ↓                ↓
        Councilor A      Councilor B      Councilor C
             │                │                │
             ↓                ↓                ↓
         Revised A        Revised B        Revised C
             │                │                │
             └────────────────┼────────────────┘
                              ↓
                         Orchestrator
                  reviews proposals, critiques,
                     revisions, and evidence
                              │
                              ↓
                 Updated Policy + State + Findings
```

## Overall iteration loop 

After each council round, the updated Extraction Policy will be applied to the next batch of Discovery samples and a fresh batch of unlabeled challenge samples. The resulting extractions will become evidence for the following council round. 

The human will check each iteration result for any errors or tweaks that need to be applied in preparation for the next. Iterations will continue under human supervision until policy changes become marginal or the observed failure modes appear sufficiently stable. 

```
       ┌───────────────────────────────┐
       │ New Discovery batch           │◄─────────────────────┐
       │ + Current Experiment State    │                      │
       │ + previous Extraction Results │                      │
       └──────────────┬────────────────┘                      │
                      ↓                                       │
                   Council                                    │
          Independent → Critique → Revise                     │
                      ↓                                       │
                 Orchestrator                                 │
                      ↓                                       │
          Updated Policy + State + Findings                   │
                      ↓                                       │
             Reference Extractor                              │
                      ↓                                       │
             Extraction Results                               │
                      ↓                                       │
             Human Review (if any) ───────────────────────────┘
```

# Expected outputs 

Phase 1 should produce: 

* a mature extraction policy   
* identified corrections to gold annotations   
* identified schema limitations or proposed revisions   
* a reproducible record of the main experimental iterations 

# Other implementation details 

## Rule-based policy format 

A policy like 

```
R1 - Do not use the filename, directory structure, source-document metadata, or external knowledge. These are not provided as evidence.    
R2 - Extract only information supported by the Data Snapshot.    
R3 - ...   
```

gives the agents a stable vocabulary for arguing. Rule IDs remain persistent across rounds. An amendment to an existing rule does not necessitate a new rule ID. If a rule is removed, retire it rather than reusing the ID. That will make the deliberation record and experiment history much easier to follow. 

This also provides an experiment-progress signal. We can count the number of new/amended/retired/active rules per round. A decay towards zero is a meaningful signal and can be the primary experiment stopping criterion.