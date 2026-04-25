<template>
    <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6">
        <a-form-item :label="label" class="filter-item">
            <slot />
        </a-form-item>
    </a-col>
</template>

<script setup lang="ts">
defineProps<{
    label: string
}>()
</script>
