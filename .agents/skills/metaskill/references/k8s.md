# k8s / infra project harness specialization rules

An infra project's harness carries heavier guardrails than a code project's. Reason: the blast radius of a mistake is not the repository but the running system.

## Guardrail reinforcement (added to root §3)

- **Separate reads from writes**: Inspection (`kubectl get/describe`, `aws ... describe-*`, `terraform plan`) is free. Changes (`apply`, `delete`, `terraform apply`) all require user confirmation. No exceptions (confirmed 2026-07-12).
- **Mandatory namespace/context specification**: Every kubectl command states `--context` and `-n` explicitly. Implicit reliance on the current context is the top cause of production mis-operation.
- **Declarative first**: Prefer manifest edits + GitOps reconciliation over imperative patches (`kubectl edit/patch`). Reason: imperative changes get silently rolled back at the next sync.
- Secrets must never be recorded in plaintext in manifests, the harness, or `_workspace/`. Follow the project standard such as Sealed Secrets / External Secrets.

## Agent/skill composition hints

- Start with a **single agent + read-only tools** initially.
- Useful skill candidates (record in the sub AGENTS.md; creation deferred — ADR 007): cluster status summary, manifest diff review (generate-verify pattern), pre-deployment checklist.
- Exclude change-class commands from agent tools whitelists by default; grant them only to individual agents when needed (tools are the number-one guardrail).

## Related-project routing

- Web/app deployment requests are mostly cross-project (e.g. web build → k8s manifest → gitops reconciliation). Always cross-record them in REGISTRY.md's "related projects" column.
- Cross-deployment work defaults to orchestrate's pipeline pattern (build → manifest → reconcile is the only logical order).
