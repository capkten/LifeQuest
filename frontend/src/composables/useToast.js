import { ref, onUnmounted } from 'vue'

/**
 * Composable for toast notifications with auto-dismiss.
 * Eliminates duplicated toast logic between Shop.vue and Backpack.vue.
 */
export function useToast() {
  const successToast = ref(null)
  const successToastTimeout = ref(null)
  const errorToast = ref(null)
  const errorToastTimeout = ref(null)

  function showSuccess(message) {
    successToast.value = message
    if (successToastTimeout.value) clearTimeout(successToastTimeout.value)
    successToastTimeout.value = setTimeout(() => {
      successToast.value = null
      successToastTimeout.value = null
    }, 3000)
  }

  function showError(message) {
    errorToast.value = message
    if (errorToastTimeout.value) clearTimeout(errorToastTimeout.value)
    errorToastTimeout.value = setTimeout(() => {
      errorToast.value = null
      errorToastTimeout.value = null
    }, 4000)
  }

  onUnmounted(() => {
    if (successToastTimeout.value) clearTimeout(successToastTimeout.value)
    if (errorToastTimeout.value) clearTimeout(errorToastTimeout.value)
  })

  return {
    successToast,
    errorToast,
    showSuccess,
    showError
  }
}
