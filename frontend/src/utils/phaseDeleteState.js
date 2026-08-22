export function createPhaseDeleteState() {
  return {
    open: false,
    pending: false,
    phase: null,
    error: null,
  }
}

export function reducePhaseDeleteState(state, event) {
  switch (event.type) {
    case 'open':
      if (state.pending) return state
      return { open: true, pending: false, phase: event.phase, error: null }
    case 'start':
      if (!state.open || !state.phase || state.pending) return state
      return { ...state, pending: true, error: null }
    case 'fail':
      if (!state.pending) return state
      return { ...state, pending: false, error: event.error }
    case 'succeed':
      return createPhaseDeleteState()
    case 'close':
      if (state.pending) return state
      return createPhaseDeleteState()
    default:
      return state
  }
}
