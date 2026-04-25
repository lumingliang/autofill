<template>
  <div class="avatar-upload-wrapper">
    <!-- 拖拽上传区域 -->
    <div ref="dropZoneRef" class="avatar-upload-container" :class="{
      'is-dragging': isDragging,
      'is-uploading': isUploading,
      'has-image': modelValue,
    }" :style="containerStyle" @click="handleClick">
      <!-- 当前头像显示 -->
      <n-avatar v-if="modelValue && !previewUrl" :src="modelValue" :size="size" round class="current-avatar"
        @click.stop />

      <!-- 预览图片（上传中或裁剪时） -->
      <img v-if="previewUrl" :src="previewUrl" class="preview-image"
        :style="{ width: `${size}px`, height: `${size}px` }" @click.stop />

      <!-- 遮罩层 -->
      <div class="upload-overlay">
        <div class="overlay-content">
          <n-icon :size="iconSize" class="upload-icon">
            <icon-mdi:cloud-upload-outline v-if="!isUploading" />
            <icon-mdi:loading v-else class="spin-animation" />
          </n-icon>
          <span class="upload-text">
            {{ isUploading ? uploadText : placeholderText }}
          </span>
          <span v-if="!isUploading && showHint" class="upload-hint">
            {{ hintText }}
          </span>
        </div>
      </div>

      <!-- 删除按钮 -->
      <div v-if="modelValue && showDelete" class="delete-btn" @click.stop="handleDelete">
        <n-icon :size="16">
          <icon-mdi:close />
        </n-icon>
      </div>
    </div>

    <!-- 隐藏的文件输入 -->
    <input ref="fileInputRef" type="file" accept="image/*" class="hidden-input" @change="handleFileChange" />

    <!-- 裁剪弹窗 -->
    <n-modal v-model:show="showCropModal" preset="card" :style="{ width: '500px' }" :title="cropTitle" :bordered="false"
      :mask-closable="false">
      <div class="crop-container">
        <img ref="cropImageRef" :src="cropImageUrl" class="crop-image" />
      </div>
      <template #footer>
        <div class="flex justify-end gap-2">
          <n-button @click="showCropModal = false">
            {{ cancelText }}
          </n-button>
          <n-button type="primary" :loading="isUploading" @click="handleCropConfirm">
            {{ confirmText }}
          </n-button>
        </div>
      </template>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Cropper from 'cropperjs'
import 'cropperjs/dist/cropper.css'

const props = defineProps({
  modelValue: { type: String, default: '' },
  size: { type: Number, default: 120 },
  iconSize: { type: Number, default: 32 },
  showDelete: { type: Boolean, default: true },
  showHint: { type: Boolean, default: true },
  placeholderText: { type: String, default: '' },
  hintText: { type: String, default: '' },
  uploadText: { type: String, default: '' },
  cropTitle: { type: String, default: '' },
  confirmText: { type: String, default: '' },
  cancelText: { type: String, default: '' },
  maxSize: { type: Number, default: 5 * 1024 * 1024 }, // 5MB
  allowedTypes: {
    type: Array,
    default: () => ['image/jpeg', 'image/png', 'image/gif', 'image/webp'],
  },
  enableCrop: { type: Boolean, default: true },
  cropAspectRatio: { type: Number, default: 1 }, // 1:1 正方形
  uploadAction: {
    type: Function,
    required: true,
  },
})

const emit = defineEmits(['update:modelValue', 'change', 'success', 'error', 'delete'])

const { t } = useI18n()

// 响应式文本
const defaultPlaceholder = computed(() => props.placeholderText || t('components.upload.placeholder') || '点击或拖拽上传')
const defaultHint = computed(() => props.hintText || t('components.upload.hint') || '支持 JPG、PNG、GIF，最大 5MB')
const defaultUploading = computed(() => props.uploadText || t('components.upload.uploading') || '上传中...')
const defaultCropTitle = computed(() => props.cropTitle || t('components.upload.crop') || '裁剪头像')
const defaultConfirm = computed(() => props.confirmText || t('common.buttons.confirm') || '确定')
const defaultCancel = computed(() => props.cancelText || t('common.buttons.cancel') || '取消')

// 实际使用的文本
const placeholderText = computed(() => props.modelValue ? t('components.upload.change') || '更换头像' : defaultPlaceholder.value)
const hintText = computed(() => defaultHint.value)
const uploadText = computed(() => defaultUploading.value)
const cropTitle = computed(() => defaultCropTitle.value)
const confirmText = computed(() => defaultConfirm.value)
const cancelText = computed(() => defaultCancel.value)

// 状态
const isDragging = ref(false)
const isUploading = ref(false)
const previewUrl = ref('')
const showCropModal = ref(false)
const cropImageUrl = ref('')
const fileInputRef = ref(null)
const dropZoneRef = ref(null)
const cropImageRef = ref(null)
let cropper = null

// 容器样式
const containerStyle = computed(() => ({
  width: `${props.size}px`,
  height: `${props.size}px`,
}))

// 拖拽事件处理
function handleDragEnter(e) {
  e.preventDefault()
  e.stopPropagation()
  isDragging.value = true
}

function handleDragLeave(e) {
  e.preventDefault()
  e.stopPropagation()
  if (!dropZoneRef.value.contains(e.relatedTarget)) {
    isDragging.value = false
  }
}

function handleDragOver(e) {
  e.preventDefault()
  e.stopPropagation()
}

function handleDrop(e) {
  e.preventDefault()
  e.stopPropagation()
  isDragging.value = false

  const files = e.dataTransfer.files
  if (files.length > 0) {
    processFile(files[0])
  }
}

// 点击上传
function handleClick() {
  if (!isUploading.value) {
    fileInputRef.value?.click()
  }
}

// 文件选择
function handleFileChange(e) {
  const file = e.target.files[0]
  if (file) {
    processFile(file)
  }
  // 重置 input 以便可以重复选择同一文件
  e.target.value = ''
}

// 验证文件
function validateFile(file) {
  if (!props.allowedTypes.includes(file.type)) {
    const allowedExt = props.allowedTypes.map(t => t.split('/')[1].toUpperCase()).join(', ')
    $message.error(t('components.upload.typeError') || `请上传 ${allowedExt} 格式的图片`)
    return false
  }
  if (file.size > props.maxSize) {
    $message.error(t('components.upload.sizeError') || `图片大小不能超过 ${props.maxSize / 1024 / 1024}MB`)
    return false
  }
  return true
}

// 处理文件
function processFile(file) {
  if (!validateFile(file)) return

  const reader = new FileReader()
  reader.onload = (e) => {
    if (props.enableCrop) {
      cropImageUrl.value = e.target.result
      showCropModal.value = true
    } else {
      uploadFile(file)
    }
  }
  reader.readAsDataURL(file)
}

// 初始化裁剪器
watch(showCropModal, (val) => {
  if (val) {
    nextTick(() => {
      if (cropImageRef.value) {
        cropper = new Cropper(cropImageRef.value, {
          aspectRatio: props.cropAspectRatio,
          viewMode: 1,
          dragMode: 'move',
          autoCropArea: 1,
          restore: false,
          guides: true,
          center: true,
          highlight: false,
          cropBoxMovable: true,
          cropBoxResizable: true,
          toggleDragModeOnDblclick: false,
        })
      }
    })
  } else {
    cropper?.destroy()
    cropper = null
  }
})

// 确认裁剪并上传
async function handleCropConfirm() {
  if (!cropper) return

  isUploading.value = true
  try {
    // 获取裁剪后的图片 Blob
    const canvas = cropper.getCroppedCanvas({
      width: props.size * 2,
      height: props.size * 2,
    })

    canvas.toBlob(async (blob) => {
      if (!blob) {
        isUploading.value = false
        return
      }

      // 创建 File 对象
      const file = new File([blob], 'cropped-avatar.png', { type: 'image/png' })
      await uploadFile(file)
      showCropModal.value = false
    }, 'image/png')
  } catch (error) {
    isUploading.value = false
    $message.error(t('components.upload.cropError') || '裁剪失败')
  }
}

// 上传文件
async function uploadFile(file) {
  isUploading.value = true
  previewUrl.value = URL.createObjectURL(file)

  try {
    const result = await props.uploadAction(file)

    if (result.code === 200) {
      let url = result.data?.url || result.data?.avatar_url
      // 添加时间戳防止浏览器缓存
      const timestamp = new Date().getTime()
      url = url.includes('?') ? `${url}&t=${timestamp}` : `${url}?t=${timestamp}`
      emit('update:modelValue', url)
      emit('change', url)
      emit('success', result)
      $message.success(t('components.upload.success') || '上传成功')
    } else {
      throw new Error(result.msg || '上传失败')
    }
  } catch (error) {
    emit('error', error)
    $message.error(error.message || t('components.upload.error') || '上传失败')
  } finally {
    isUploading.value = false
    previewUrl.value = ''
  }
}

// 删除头像
function handleDelete() {
  emit('update:modelValue', '')
  emit('change', '')
  emit('delete')
  $message.success(t('components.upload.deleted') || '已删除')
}

// 绑定拖拽事件
onMounted(() => {
  const dropZone = dropZoneRef.value
  if (dropZone) {
    dropZone.addEventListener('dragenter', handleDragEnter)
    dropZone.addEventListener('dragleave', handleDragLeave)
    dropZone.addEventListener('dragover', handleDragOver)
    dropZone.addEventListener('drop', handleDrop)
  }
})

onUnmounted(() => {
  const dropZone = dropZoneRef.value
  if (dropZone) {
    dropZone.removeEventListener('dragenter', handleDragEnter)
    dropZone.removeEventListener('dragleave', handleDragLeave)
    dropZone.removeEventListener('dragover', handleDragOver)
    dropZone.removeEventListener('drop', handleDrop)
  }
  cropper?.destroy()
})
</script>

<style scoped lang="scss">
.avatar-upload-wrapper {
  display: inline-block;
}

.avatar-upload-container {
  position: relative;
  border-radius: 50%;
  overflow: hidden;
  cursor: pointer;
  border: 2px dashed #d9d9d9;
  transition: all 0.3s ease;
  background-color: #fafafa;

  &:hover {
    border-color: #4096ff;

    .upload-overlay {
      opacity: 1;
    }
  }

  &.is-dragging {
    border-color: #4096ff;
    background-color: #e6f4ff;
  }

  &.is-uploading {
    cursor: not-allowed;
  }

  &.has-image {
    border-style: solid;
    border-color: #d9d9d9;

    &:hover {
      border-color: #4096ff;
    }
  }
}

.current-avatar,
.preview-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.upload-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.3s ease;

  .has-image & {
    opacity: 0;
  }

  .has-image:hover & {
    opacity: 1;
  }

  .is-uploading & {
    opacity: 1;
    background-color: rgba(0, 0, 0, 0.65);
  }
}

.overlay-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  color: #fff;
  text-align: center;
  padding: 8px;
}

.upload-icon {
  margin-bottom: 8px;
}

.upload-text {
  font-size: 14px;
  font-weight: 500;
}

.upload-hint {
  font-size: 12px;
  margin-top: 4px;
  opacity: 0.8;
}

.hidden-input {
  display: none;
}

.delete-btn {
  position: absolute;
  top: -8px;
  right: -8px;
  width: 24px;
  height: 24px;
  background-color: #ff4d4f;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.3s ease;
  z-index: 10;

  &:hover {
    background-color: #ff7875;
  }

  .avatar-upload-container:hover & {
    opacity: 1;
  }
}

.spin-animation {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }

  to {
    transform: rotate(360deg);
  }
}

.crop-container {
  width: 100%;
  height: 400px;

  .crop-image {
    max-width: 100%;
    display: block;
  }
}

:deep(.cropper-container) {
  width: 100% !important;
  height: 100% !important;
}

:deep(.cropper-crop-box) {
  border-radius: 50%;
}
</style>
