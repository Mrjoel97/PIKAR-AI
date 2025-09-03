// Minimal agent SDK facade to satisfy imports and provide no-op behavior
export const agentSDK = {
  async createConversation({ agent_name, metadata }) {
    return { id: `conv_${Date.now()}`, agent_name, metadata, messages: [] }
  },
  subscribeToConversation(conversationId, cb) {
    const interval = setInterval(() => cb({ id: conversationId, messages: [] }), 60000)
    return () => clearInterval(interval)
  },
  async addMessage(conversation, { role, content }) {
    return { ok: true }
  }
}

export default agentSDK

