export function createSequencedRequest({ onStart, onSuccess, onError, onFinish }) {
  let sequence = 0

  async function run(request) {
    const requestId = ++sequence
    onStart()
    try {
      const result = await request()
      if (requestId !== sequence) return false
      onSuccess(result)
      return true
    } catch (error) {
      if (requestId !== sequence) return false
      onError(error)
      return false
    } finally {
      if (requestId === sequence) onFinish()
    }
  }

  run.cancel = () => {
    sequence += 1
  }

  return run
}
