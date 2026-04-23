<template>
  <PageHeader
    class="page-header"
    :title="title"
    :sub-title="subtitle"
    @back="onBack"
  >
    <template #extra>
      <slot name="extra" />
    </template>
  </PageHeader>
</template>

<script setup>
import { PageHeader } from 'ant-design-vue'

defineProps({
  title: { type: String, default: '实时语音' },
  subtitle: { type: String, default: '' }
})

const emit = defineEmits(['back'])

const onBack = () => {
  emit('back')
}
</script>

<style scoped>
.page-header {
  background: var(--header-bg);
  border-bottom: 1px solid var(--border-color);
  padding: 0 16px;
  height: var(--header-height);
  line-height: var(--header-height);
}

.page-header :deep(.ant-page-header-heading) {
  height: var(--header-height);
  line-height: var(--header-height);
}

.page-header :deep(.ant-page-header-heading-title) {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}
</style>