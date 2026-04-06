# Scout Guide: Building Autonomous Researchers

## The Scout Lifecycle
1. **configure()**: Load perimeter YAML.
2. **discover()**: Navigate to target URL/Feed.
3. **extract()**: Pull information from raw data.
4. **evaluate()**: Check the "Surprise Metric."
5. **dream()**: If signal is low, hypothesize.
6. **submit()**: Pass verified intelligence to the ledger.

## Writing a Custom Scout
To write a new scout, inherit from `BaseScout` and implement:
- `discover(params)`
- `extract(raw_data)`
- `mutate_params(old_params, hunch)`

## Adaptive RAG Patterns
Always summarize with a local model first. Only send the high-signal "Pulse" to the Central Brain. This protects the swarm from $1,000+ daily API costs.
