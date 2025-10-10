For Testing.

```
curl -X POST http://localhost:10001/ \
  -H "Content-Type: application/json" \
  -d '{
        "jsonrpc": "2.0",
        "id": "test-001",
        "method": "message/send",
        "params": {
          "message": {
            "messageId": "msg-001",
            "role": "user",
            "parts": [
              {
                "kind": "text",
                "text": "고객: 안녕하세요? 상담사: 네, 무엇을 도와드릴까요?"
              }
            ]
          }
        }
      }'
```
