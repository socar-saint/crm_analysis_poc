# VOC Agent Demo Scripts

Run the single-turn client with your message:

```
uv run python -m voc_agent.demo.single_turn_client "이 파일 처리해줘: /path/상담내역1.opus"
```

Optional flags:
- `--speakers` to label speakers (default: `상담사,고객`)
- `--agent-url` to point at a different orchestrator URL
