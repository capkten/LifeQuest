export function createMcpTokenState() {
  return {
    mcpTokens: [],
    mcpTokensLoading: false,
    mcpTokensError: null,
    mcpTokenForm: {
      name: '',
      expires_in_days: 90
    },
    mcpTokenCreating: false,
    newMcpToken: null,
    revokeTarget: null,
    mcpTokenRevoking: false,
    mcpTokenCopying: false,
    mcpTokenCopyStatus: 'idle'
  }
}

export function reduceMcpTokenState(state, action) {
  switch (action.type) {
    case 'list-start':
      return state.mcpTokensLoading ? state : {
        ...state,
        mcpTokensLoading: true,
        mcpTokensError: null
      }
    case 'list-success':
      return {
        ...state,
        mcpTokens: Array.isArray(action.tokens) ? action.tokens : [],
        mcpTokensLoading: false,
        mcpTokensError: null
      }
    case 'list-failure':
      return {
        ...state,
        mcpTokensLoading: false,
        mcpTokensError: action.error
      }
    case 'create-start':
      return state.mcpTokenCreating ? state : { ...state, mcpTokenCreating: true }
    case 'create-success':
      return {
        ...state,
        mcpTokenCreating: false,
        newMcpToken: action.token,
        mcpTokenCopying: false,
        mcpTokenCopyStatus: 'idle'
      }
    case 'create-failure':
      return { ...state, mcpTokenCreating: false }
    case 'new-token':
      return {
        ...state,
        newMcpToken: action.token,
        mcpTokenCopying: false,
        mcpTokenCopyStatus: 'idle'
      }
    case 'clear-new-token':
      return { ...state, newMcpToken: null }
    case 'copy-start':
      return state.mcpTokenCopying || state.mcpTokenRevoking ? state : {
        ...state,
        mcpTokenCopying: true,
        mcpTokenCopyStatus: 'pending'
      }
    case 'copy-success':
      return { ...state, mcpTokenCopyStatus: 'success' }
    case 'copy-failure':
      return { ...state, mcpTokenCopyStatus: 'failure' }
    case 'copy-finish':
      return { ...state, mcpTokenCopying: false }
    case 'open-revoke':
      return !state.mcpTokenCopying && action.token?.status === 'active' && !action.token.revoked_at
        ? { ...state, revokeTarget: action.token }
        : state
    case 'close-revoke':
      return state.mcpTokenRevoking ? state : { ...state, revokeTarget: null }
    case 'revoke-start':
      return state.mcpTokenRevoking || state.mcpTokenCopying || !state.revokeTarget
        ? state
        : { ...state, mcpTokenRevoking: true }
    case 'revoke-success':
      return {
        ...state,
        revokeTarget: null,
        newMcpToken: state.newMcpToken?.id === action.tokenId ? null : state.newMcpToken
      }
    case 'revoke-failure':
      return state
    case 'revoke-finish':
      return { ...state, mcpTokenRevoking: false }
    default:
      return state
  }
}
