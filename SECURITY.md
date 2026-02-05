# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in Jarvis Assistant, please report it by:

1. **Email**: Send details to the repository maintainer (DO NOT open a public issue)
2. **Include**: 
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

## Security Best Practices

When using Jarvis Assistant:

### API Keys & Secrets
- **Never commit** API keys, tokens, or credentials to the repository
- Use `.env` files or `key.txt` for local development
- Use environment variables in production
- Rotate keys regularly

### Voice & Microphone Access
- The assistant requires microphone access for voice commands
- Review the code to understand what audio is processed
- Consider using local LLMs for sensitive conversations
- Audio is not stored by default

### Tool Permissions
- Review tool permissions before enabling sensitive operations
- The safety layer requests confirmation for system-level actions
- Customize `assistant/safety/permissions.py` for your security needs

### Network Communication
- By default, uses Google's Speech Recognition API
- LM Studio can run entirely offline for privacy
- Review network requests in the codebase

### Memory & Data Storage
- Assistant memory is stored locally in `assistant_memory.json`
- No data is sent to third parties except:
  - Speech recognition API (Google)
  - LLM API (Gemini or LM Studio)
  - Tool-specific APIs (search engines, etc.)

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| main    | ✅ Active development |

## Known Considerations

1. **Local Execution**: This assistant executes code locally based on voice commands. Review all tool implementations.
2. **API Usage**: External APIs may log requests according to their policies.
3. **Wake Word**: Porcupine wake word detection is always listening when active.

## Updates

This security policy will be updated as the project evolves.
