# Agent specification

## Common output schema (for all agents except SummaryAgent)

```json
{
  "summary": "string",
  "comments": [
    {
      "path": "string",
      "line": 1,
      "agent": "StyleAgent|BugRiskAgent|PerformanceAgent|SecurityAgent",
      "level": "info|warn|blocking",
      "body": "string"
    }
  ],
  "blocking": false
}
```

## SummaryAgent output schema

```json
{
  "summary": "string (3-5 bullet lines)",
  "comments": [],
  "blocking": false
}
```
