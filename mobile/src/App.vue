<script setup lang="ts">
import { onLaunch, onShow } from '@dcloudio/uni-app'
import { useAuthStore } from '@/stores/auth'

onLaunch(() => {
  const auth = useAuthStore()
  auth.initAuth()
})

onShow(() => {
  // 应用从后台进入前台
})
</script>

<style lang="scss">
@import '@/styles/global.scss';
</style>
