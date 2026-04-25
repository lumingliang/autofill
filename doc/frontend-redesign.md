# AI平台前端改造设计文档

## 1. 项目概述

### 1.1 改造目标
将现有的 "Vue FastAPI Admin" 后台管理系统改造为 "AI平台"，移除框架相关的品牌元素，简化界面，增加文件上传和头像修改功能。

### 1.2 技术栈
- **前端框架**: Vue 3 + Vite
- **UI组件库**: Naive UI
- **状态管理**: Pinia
- **样式**: UnoCSS + SCSS
- **国际化**: Vue I18n (将移除)

---

## 2. 需求分析

### 2.1 需要删除的元素

| 位置 | 元素 | 说明 |
|------|------|------|
| 顶部导航栏 | GithubSite 组件 | GitHub跳转链接 |
| 顶部导航栏 | Languages 组件 | 中英文切换功能 |
| 顶部导航栏 | 系统Logo图标 | SideLogo中的icon-custom-logo |
| 登录页 | 系统Logo图标 | icon-custom-logo |
| 工作台 | 项目卡片区域 | 9个Vue FastAPI Admin卡片 |
| 工作台 | 统计信息 | 项目数、待办、消息 |
| 系统名称 | Vue FastAPI Admin | 所有显示位置 |

### 2.2 需要修改的内容

| 位置 | 原内容 | 新内容 |
|------|--------|--------|
| 系统名称 | Vue FastAPI Admin | AI平台 |
| 环境变量 | VITE_TITLE | AI平台 |
| 欢迎页面 | 复杂的工作台 | 简单的欢迎语 |
| 个人中心 | 仅显示头像 | 支持头像上传修改 |

### 2.3 需要新增的功能

| 功能 | 描述 | 优先级 |
|------|------|--------|
| 文件上传配置 | 后端配置上传目录，保存到本地 | 高 |
| 头像上传 | 用户可上传修改个人头像 | 高 |
| 上传组件 | 通用的文件上传组件 | 中 |

---

## 3. 详细设计方案

### 3.1 布局改造

#### 3.1.1 顶部导航栏 (Header)
**文件**: `web/src/layout/components/header/index.vue`

**改造内容**:
```vue
<!-- 删除前 -->
<div ml-auto flex items-center>
  <TenantSelector v-if="userStore.tenants.length > 1" />
  <Languages />           <!-- 删除 -->
  <ThemeMode />
  <GithubSite />          <!-- 删除 -->
  <FullScreen />
  <UserAvatar />
</div>

<!-- 删除后 -->
<div ml-auto flex items-center>
  <TenantSelector v-if="userStore.tenants.length > 1" />
  <ThemeMode />
  <FullScreen />
  <UserAvatar />
</div>
```

#### 3.1.2 侧边栏Logo (SideLogo)
**文件**: `web/src/layout/components/sidebar/components/SideLogo.vue`

**改造内容**:
```vue
<!-- 删除前 -->
<router-link h-60 f-c-c to="/">
  <icon-custom-logo text-36 color-primary></icon-custom-logo>  <!-- 删除 -->
  <h2 v-show="!appStore.collapsed" ml-2 mr-8 ...>
    {{ title }}
  </h2>
</router-link>

<!-- 删除后 -->
<router-link h-60 f-c-c to="/">
  <h2 v-show="!appStore.collapsed" ml-2 mr-8 ...>
    {{ title }}
  </h2>
</router-link>
```

### 3.2 页面改造

#### 3.2.1 登录页
**文件**: `web/src/views/login/index.vue`

**改造内容**:
```vue
<!-- 删除前 -->
<h5 f-c-c text-24 font-normal color="#6a6a6a">
  <icon-custom-logo mr-10 text-50 color-primary />{{ $t('app_name') }}
</h5>

<!-- 删除后 -->
<h5 f-c-c text-24 font-normal color="#6a6a6a">
  AI平台
</h5>
```

#### 3.2.2 工作台/欢迎页
**文件**: `web/src/views/workbench/index.vue`

**改造内容**:
```vue
<template>
  <AppPage :show-footer="false">
    <div flex-1 f-c-c>
      <n-card rounded-10 class="text-center p-20">
        <h1 text-32 font-bold color-primary>欢迎使用 AI平台</h1>
        <p mt-10 text-16 op-60>Welcome to AI Platform</p>
      </n-card>
    </div>
  </AppPage>
</template>
```

#### 3.2.3 个人中心
**文件**: `web/src/views/profile/index.vue`

**改造内容**:
- 头像显示改为头像上传组件
- 支持点击上传新头像
- 预览上传的图片
- 保存时同步更新用户头像

```vue
<NFormItem :label="$t('views.profile.label_avatar')" path="avatar">
  <div class="flex items-center gap-4">
    <NImage width="100" :src="infoForm.avatar"></NImage>
    <n-upload
      accept="image/*"
      :action="uploadUrl"
      :headers="uploadHeaders"
      :on-finish="handleAvatarUploadFinish"
      :on-error="handleAvatarUploadError"
      :show-file-list="false"
    >
      <n-button>上传新头像</n-button>
    </n-upload>
  </div>
</NFormItem>
```

### 3.3 配置文件修改

#### 3.3.1 环境变量
**文件**: `web/.env`

```bash
# 修改前
VITE_TITLE = 'Vue FastAPI Admin'

# 修改后
VITE_TITLE = 'AI平台'
```

#### 3.3.2 环境变量 (开发)
**文件**: `web/.env.development`

```bash
VITE_TITLE = 'AI平台'
```

#### 3.3.3 环境变量 (生产)
**文件**: `web/.env.production`

```bash
VITE_TITLE = 'AI平台'
```

### 3.4 国际化文件修改

#### 3.4.1 中文语言包
**文件**: `web/i18n/messages/cn.json`

```json
{
  "lang": "中文",
  "app_name": "AI平台",
  "header": {
    "label_profile": "个人信息",
    "label_logout": "退出登录",
    "label_logout_dialog_title": "提示",
    "text_logout_confirm": "确认退出？",
    "text_logout_success": "已退出登录"
  },
  "views": {
    "login": {
      "text_login": "登录",
      "message_input_username_password": "请输入用户名和密码",
      "message_verifying": "正在验证...",
      "message_login_success": "登录成功"
    },
    "workbench": {
      "label_workbench": "工作台",
      "text_hello": "您好，{username}",
      "text_welcome": "欢迎使用 AI平台",
      "label_number_of_items": "项目数",
      "label_upcoming": "待办",
      "label_information": "消息",
      "label_project": "项目",
      "label_more": "更多"
    },
    "profile": {
      "label_profile": "个人中心",
      "label_modify_information": "修改信息",
      "label_change_password": "修改密码",
      "label_avatar": "头像",
      "label_username": "用户姓名",
      "label_email": "邮箱",
      "label_old_password": "旧密码",
      "label_new_password": "新密码",
      "label_confirm_password": "确认密码",
      "placeholder_username": "请填写姓名",
      "placeholder_email": "请填写邮箱",
      "placeholder_old_password": "请输入旧密码",
      "placeholder_new_password": "请输入新密码",
      "placeholder_confirm_password": "请再次输入新密码",
      "message_username_required": "请输入昵称",
      "message_old_password_required": "请输入旧密码",
      "message_new_password_required": "请输入新密码",
      "message_password_confirmation_required": "请再次输入密码",
      "message_password_confirmation_diff": "两次密码输入不一致",
      "label_upload_avatar": "上传头像",
      "message_upload_success": "头像上传成功",
      "message_upload_error": "头像上传失败"
    },
    "errors": {
      "label_error": "错误页",
      "text_back_to_home": "返回首页"
    }
  },
  "common": {
    "text": {
      "update_success": "修改成功"
    },
    "buttons": {
      "update": "修改",
      "upload": "上传"
    }
  }
}
```

#### 3.4.2 英文语言包
**文件**: `web/i18n/messages/en.json`

```json
{
  "lang": "English",
  "app_name": "AI Platform",
  "header": {
    "label_profile": "Profile",
    "label_logout": "Logout",
    "label_logout_dialog_title": "Confirm",
    "text_logout_confirm": "Are you sure to logout?",
    "text_logout_success": "Logout successful"
  },
  "views": {
    "login": {
      "text_login": "Login",
      "message_input_username_password": "Please input username and password",
      "message_verifying": "Verifying...",
      "message_login_success": "Login successful"
    },
    "workbench": {
      "label_workbench": "Workbench",
      "text_hello": "Hello, {username}",
      "text_welcome": "Welcome to AI Platform",
      "label_number_of_items": "Items",
      "label_upcoming": "Upcoming",
      "label_information": "Messages",
      "label_project": "Projects",
      "label_more": "More"
    },
    "profile": {
      "label_profile": "Profile",
      "label_modify_information": "Modify Information",
      "label_change_password": "Change Password",
      "label_avatar": "Avatar",
      "label_username": "Username",
      "label_email": "Email",
      "label_old_password": "Old Password",
      "label_new_password": "New Password",
      "label_confirm_password": "Confirm Password",
      "placeholder_username": "Please input username",
      "placeholder_email": "Please input email",
      "placeholder_old_password": "Please input old password",
      "placeholder_new_password": "Please input new password",
      "placeholder_confirm_password": "Please confirm new password",
      "message_username_required": "Please input username",
      "message_old_password_required": "Please input old password",
      "message_new_password_required": "Please input new password",
      "message_password_confirmation_required": "Please confirm password",
      "message_password_confirmation_diff": "Passwords do not match",
      "label_upload_avatar": "Upload Avatar",
      "message_upload_success": "Avatar uploaded successfully",
      "message_upload_error": "Avatar upload failed"
    },
    "errors": {
      "label_error": "Error",
      "text_back_to_home": "Back to Home"
    }
  },
  "common": {
    "text": {
      "update_success": "Update successful"
    },
    "buttons": {
      "update": "Update",
      "upload": "Upload"
    }
  }
}
```

### 3.5 后端上传配置

#### 3.5.1 配置文件
**文件**: `config.toml`

```toml
[upload]
# 上传文件保存目录
upload_dir = "./uploads"
# 头像保存子目录
avatar_dir = "./uploads/avatars"
# 允许的文件类型
allowed_extensions = ["jpg", "jpeg", "png", "gif", "webp"]
# 最大文件大小 (MB)
max_file_size = 5
# 文件访问URL前缀
file_url_prefix = "/uploads"
```

#### 3.5.2 上传API设计

**接口**: `POST /api/v1/upload`

**请求**:
```http
POST /api/v1/upload
Content-Type: multipart/form-data

file: <二进制文件>
type: "avatar" | "file"  # 上传类型
```

**响应**:
```json
{
  "code": 200,
  "message": "上传成功",
  "data": {
    "url": "/uploads/avatars/xxx.jpg",
    "filename": "xxx.jpg",
    "size": 1024,
    "mimetype": "image/jpeg"
  }
}
```

**接口**: `POST /api/v1/upload/avatar`

**请求**:
```http
POST /api/v1/upload/avatar
Content-Type: multipart/form-data
Authorization: Bearer <token>

file: <图片文件>
```

**响应**:
```json
{
  "code": 200,
  "message": "头像上传成功",
  "data": {
    "avatar_url": "/uploads/avatars/xxx.jpg"
  }
}
```

---

## 4. 组件设计

### 4.1 文件上传组件

**文件**: `web/src/components/upload/FileUpload.vue`

```vue
<template>
  <n-upload
    :action="action"
    :headers="headers"
    :accept="accept"
    :max-size="maxSize"
    :on-finish="handleFinish"
    :on-error="handleError"
    :before-upload="beforeUpload"
    :show-file-list="showFileList"
    :multiple="multiple"
  >
    <slot>
      <n-button>
        <template #icon>
          <TheIcon icon="material-symbols:upload" />
        </template>
        {{ buttonText }}
      </n-button>
    </slot>
  </n-upload>
</template>

<script setup>
const props = defineProps({
  action: { type: String, required: true },
  accept: { type: String, default: '*' },
  maxSize: { type: Number, default: 5 * 1024 * 1024 }, // 5MB
  buttonText: { type: String, default: '上传文件' },
  showFileList: { type: Boolean, default: false },
  multiple: { type: Boolean, default: false },
})

const emit = defineEmits(['success', 'error'])

const headers = computed(() => ({
  Authorization: `Bearer ${getToken()}`
}))

function handleFinish({ file, event }) {
  const response = JSON.parse(event.target.response)
  emit('success', response.data)
}

function handleError({ file, event }) {
  emit('error', event)
}

function beforeUpload({ file }) {
  if (file.file?.size > props.maxSize) {
    $message.error('文件大小超过限制')
    return false
  }
  return true
}
</script>
```

### 4.2 头像上传组件

**文件**: `web/src/components/upload/AvatarUpload.vue`

```vue
<template>
  <div class="flex items-center gap-4">
    <n-avatar
      :src="modelValue"
      :size="size"
      round
      class="cursor-pointer"
      @click="handlePreview"
    />
    <n-upload
      accept="image/*"
      :action="uploadAction"
      :headers="headers"
      :show-file-list="false"
      :on-finish="handleUploadFinish"
      :on-error="handleUploadError"
      :before-upload="beforeUpload"
    >
      <n-button size="small">
        <template #icon>
          <TheIcon icon="material-symbols:upload" :size="16" />
        </template>
        更换头像
      </n-button>
    </n-upload>
    
    <!-- 图片预览 -->
    <n-image
      v-show="false"
      ref="imageRef"
      :src="modelValue"
    />
  </div>
</template>

<script setup>
const props = defineProps({
  modelValue: { type: String, default: '' },
  size: { type: Number, default: 100 },
})

const emit = defineEmits(['update:modelValue', 'change'])

const uploadAction = '/api/v1/upload/avatar'
const imageRef = ref(null)

const headers = computed(() => ({
  Authorization: `Bearer ${getToken()}`
}))

function handleUploadFinish({ event }) {
  const response = JSON.parse(event.target.response)
  if (response.code === 200) {
    emit('update:modelValue', response.data.avatar_url)
    emit('change', response.data.avatar_url)
    $message.success('头像上传成功')
  } else {
    $message.error(response.message || '上传失败')
  }
}

function handleUploadError() {
  $message.error('头像上传失败')
}

function beforeUpload({ file }) {
  const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
  if (!allowedTypes.includes(file.file?.type)) {
    $message.error('请上传图片文件')
    return false
  }
  if (file.file?.size > 5 * 1024 * 1024) {
    $message.error('图片大小不能超过5MB')
    return false
  }
  return true
}

function handlePreview() {
  imageRef.value?.click()
}
</script>
```

---

## 5. 后端实现

### 5.1 上传服务

**文件**: `app/api/v1/upload/__init__.py`

```python
from fastapi import APIRouter, UploadFile, File, Depends
from app.core.dependency import get_current_user
from app.schemas.base import ResponseSchema
import os
import uuid
from datetime import datetime

router = APIRouter()

UPLOAD_DIR = "./uploads"
AVATAR_DIR = "./uploads/avatars"
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

@router.post("/upload", summary="通用文件上传")
async def upload_file(
    file: UploadFile = File(...),
    file_type: str = "file",
    user=Depends(get_current_user)
):
    """通用文件上传接口"""
    # 检查文件类型
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        return ResponseSchema(code=400, msg="不支持的文件类型")
    
    # 检查文件大小
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        return ResponseSchema(code=400, msg="文件大小超过限制")
    
    # 生成文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    new_filename = f"{timestamp}_{uuid.uuid4().hex[:8]}{file_ext}"
    
    # 确定保存路径
    if file_type == "avatar":
        save_dir = AVATAR_DIR
    else:
        save_dir = os.path.join(UPLOAD_DIR, file_type)
    
    os.makedirs(save_dir, exist_ok=True)
    file_path = os.path.join(save_dir, new_filename)
    
    # 保存文件
    with open(file_path, "wb") as f:
        f.write(content)
    
    # 返回文件URL
    file_url = f"/uploads/{file_type}/{new_filename}" if file_type != "avatar" else f"/uploads/avatars/{new_filename}"
    
    return ResponseSchema(code=200, msg="上传成功", data={
        "url": file_url,
        "filename": new_filename,
        "size": len(content),
        "mimetype": file.content_type
    })

@router.post("/upload/avatar", summary="上传头像")
async def upload_avatar(
    file: UploadFile = File(...),
    user=Depends(get_current_user)
):
    """用户头像上传接口"""
    # 检查文件类型
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        return ResponseSchema(code=400, msg="请上传图片文件")
    
    # 检查文件大小
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        return ResponseSchema(code=400, msg="图片大小不能超过5MB")
    
    # 生成文件名: user_{user_id}_{timestamp}.ext
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    new_filename = f"user_{user.id}_{timestamp}{file_ext}"
    
    os.makedirs(AVATAR_DIR, exist_ok=True)
    file_path = os.path.join(AVATAR_DIR, new_filename)
    
    # 保存文件
    with open(file_path, "wb") as f:
        f.write(content)
    
    # 更新用户头像
    avatar_url = f"/uploads/avatars/{new_filename}"
    # TODO: 更新数据库中的用户头像
    
    return ResponseSchema(code=200, msg="头像上传成功", data={
        "avatar_url": avatar_url
    })
```

### 5.2 静态文件服务

**文件**: `app/core/init_app.py`

```python
from fastapi.staticfiles import StaticFiles

# 注册上传文件静态服务
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
```

---

## 6. 文件清单

### 6.1 需要修改的文件

| 序号 | 文件路径 | 修改类型 |
|------|----------|----------|
| 1 | `web/.env` | 修改系统名称 |
| 2 | `web/.env.development` | 修改系统名称 |
| 3 | `web/.env.production` | 修改系统名称 |
| 4 | `web/src/layout/components/header/index.vue` | 删除Languages、GithubSite组件引用 |
| 5 | `web/src/layout/components/sidebar/components/SideLogo.vue` | 删除Logo图标 |
| 6 | `web/src/views/login/index.vue` | 删除Logo图标，修改标题 |
| 7 | `web/src/views/workbench/index.vue` | 简化为欢迎页面 |
| 8 | `web/src/views/profile/index.vue` | 添加头像上传功能 |
| 9 | `web/i18n/messages/cn.json` | 修改系统名称和欢迎语 |
| 10 | `web/i18n/messages/en.json` | 修改系统名称和欢迎语 |

### 6.2 需要删除的文件

| 序号 | 文件路径 | 说明 |
|------|----------|------|
| 1 | `web/src/layout/components/header/components/GithubSite.vue` | GitHub跳转组件 |
| 2 | `web/src/layout/components/header/components/Languages.vue` | 语言切换组件 |

### 6.3 需要新增的文件

| 序号 | 文件路径 | 说明 |
|------|----------|------|
| 1 | `web/src/components/upload/FileUpload.vue` | 通用文件上传组件 |
| 2 | `web/src/components/upload/AvatarUpload.vue` | 头像上传组件 |
| 3 | `web/src/components/upload/index.js` | 组件导出 |
| 4 | `app/api/v1/upload/__init__.py` | 上传API |
| 5 | `app/api/v1/upload/upload.py` | 上传服务实现 |

---

## 7. 实施计划

### 7.1 第一阶段：界面清理
1. 修改环境变量中的系统名称
2. 删除顶部导航栏的GitHub和语言切换组件
3. 删除侧边栏和登录页的Logo图标
4. 简化工作台为欢迎页面

### 7.2 第二阶段：上传功能
1. 后端实现上传API
2. 配置上传目录和静态文件服务
3. 前端实现上传组件
4. 个人中心集成头像上传

### 7.3 第三阶段：测试优化
1. 测试所有页面显示正常
2. 测试头像上传功能
3. 测试文件上传功能
4. 优化细节和样式

---

## 8. 注意事项

1. **文件路径**: 上传的文件保存路径需要确保有写入权限
2. **文件清理**: 考虑定期清理未使用的上传文件
3. **安全性**: 上传接口需要验证用户身份，限制文件类型和大小
4. **备份**: 上传的文件目录需要纳入备份策略
5. **兼容性**: 修改后需要测试各浏览器的兼容性
