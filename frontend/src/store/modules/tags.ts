import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import router from '@/router'

export const useTagsStore = defineStore('tags', () => {
  const tags = ref<any[]>(JSON.parse(localStorage.getItem('tags') || '[]'))
  const activeTag = ref(localStorage.getItem('activeTag') || '')

  const activeIndex = computed(() => tags.value.findIndex((item) => item.path === activeTag.value))

  function setActiveTag(path: string) {
    activeTag.value = path
    localStorage.setItem('activeTag', path)
  }

  function setTags(newTags: any[]) {
    tags.value = newTags
    localStorage.setItem('tags', JSON.stringify(newTags))
  }

  function addTag(tag: any = {}) {
    setActiveTag(tag.path)
    const WITHOUT_TAG_PATHS = ['/login', '/404', '/403']
    if (WITHOUT_TAG_PATHS.includes(tag.path) || tags.value.some((item) => item.path === tag.path)) return
    setTags([...tags.value, tag])
  }

  function removeTag(path: string) {
    if (path === activeTag.value) {
      if (activeIndex.value > 0) {
        router.push(tags.value[activeIndex.value - 1].path)
      } else {
        router.push(tags.value[activeIndex.value + 1].path)
      }
    }
    setTags(tags.value.filter((tag) => tag.path !== path))
  }

  function removeOther(curPath = activeTag.value) {
    setTags(tags.value.filter((tag) => tag.path === curPath))
    if (curPath !== activeTag.value) {
      router.push(tags.value[tags.value.length - 1].path)
    }
  }

  function removeLeft(curPath: string) {
    const curIndex = tags.value.findIndex((item) => item.path === curPath)
    const filterTags = tags.value.filter((_, index) => index >= curIndex)
    setTags(filterTags)
    if (!filterTags.find((item) => item.path === activeTag.value)) {
      router.push(filterTags[filterTags.length - 1].path)
    }
  }

  function removeRight(curPath: string) {
    const curIndex = tags.value.findIndex((item) => item.path === curPath)
    const filterTags = tags.value.filter((_, index) => index <= curIndex)
    setTags(filterTags)
    if (!filterTags.find((item) => item.path === activeTag.value)) {
      router.push(filterTags[filterTags.length - 1].path)
    }
  }

  function resetTags() {
    setTags([])
    setActiveTag('')
  }

  return {
    tags,
    activeTag,
    activeIndex,
    addTag,
    removeTag,
    removeOther,
    removeLeft,
    removeRight,
    resetTags,
  }
})
