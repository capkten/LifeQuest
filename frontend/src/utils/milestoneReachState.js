export function createMilestoneReachRequestState() {
  const tokens = new Map()

  return {
    begin(milestoneId, projectId, routeRevision) {
      const key = String(milestoneId)
      const previous = tokens.get(key)
      const token = Object.freeze({
        milestoneId: key,
        sequence: (previous?.sequence || 0) + 1,
        projectId: String(projectId || ''),
        routeRevision,
      })
      tokens.set(key, token)
      return token
    },

    isCurrent(token, routeId, currentRouteRevision) {
      return Boolean(token)
        && tokens.get(token.milestoneId) === token
        && token.projectId === String(routeId || '')
        && token.routeRevision === currentRouteRevision
    },

    finish(token) {
      if (tokens.get(token?.milestoneId) === token) tokens.delete(token.milestoneId)
    },

    invalidate() {
      tokens.clear()
    },
  }
}
