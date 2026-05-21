<template>
  <div class="field-spec-management">
    <CrudTable ref="crudTableRef" :columns="columns" :data-source="tableData" :loading="loading"
      :pagination="pagination" :filter-model="queryParams" :filter-item-count="filterItemCount" show-modal
      :modal-title="modalTitle" :modal-loading="modalLoading" :modal-form="modalForm" :modal-rules="modalRules"
      modal-width="800px" :row-selection="rowSelection" @search="handleSearch" @reset="handleReset"
      @table-change="handleTableChange" @modal-ok="handleSave">
      <!-- 筛选条件 -->
      <template #filter-items>
        <a-col v-if="userStore.isSuperUser" :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="租户" class="filter-item">
            <a-select v-model:value="queryParams.tenant_id" placeholder="请选择租户" allow-clear :options="tenantOptions"
              @change="handleTenantChange" />
          </a-form-item>
        </a-col>
        <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="应用名称" class="filter-item">
            <a-select v-model:value="queryParams.app_name" placeholder="请选择应用" allow-clear :options="appOptions"
              @change="handleSearch" />
          </a-form-item>
        </a-col>
        <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="字段名" class="filter-item">
            <a-input v-model:value="queryParams.field_name" placeholder="请输入字段名" allow-clear
              @pressEnter="handleSearch" />
          </a-form-item>
        </a-col>
        <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="字段标签" class="filter-item">
            <a-input v-model:value="queryParams.field_label" placeholder="请输入字段标签" allow-clear
              @pressEnter="handleSearch" />
          </a-form-item>
        </a-col>
        <a-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" class="filter-item-col">
          <a-form-item label="字段类型" class="filter-item">
            <a-select v-model:value="queryParams.field_type" placeholder="请选择字段类型" allow-clear
              :options="fieldTypeOptions" @change="handleSearch" />
          </a-form-item>
        </a-col>
      </template>

      <!-- 操作按钮 -->
      <template #actions>
        <a-space>
          <a-button v-permission="'post/api/v1/autofill/field_spec/create'" type="primary" @click="handleAdd">
            <PlusOutlined />
            新建字段
          </a-button>
          <a-popconfirm
            title="确定批量删除选中的字段吗？"
            description="此操作不可恢复，请谨慎操作！"
            ok-text="确定"
            cancel-text="取消"
            ok-type="danger"
            @confirm="handleBatchDelete"
          >
            <a-button v-permission="'delete/api/v1/autofill/field_spec/batch_delete'" danger :disabled="selectedRowKeys.length === 0">
              <DeleteOutlined />
              批量删除
            </a-button>
          </a-popconfirm>
          <a-typography-text v-if="selectedRowKeys.length > 0" type="secondary">
            已选择 {{ selectedRowKeys.length }} 项
          </a-typography-text>
        </a-space>
      </template>

      <!-- 表格列自定义 -->
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'field_type'">
          <a-tag :color="getFieldTypeColor(record.field_type)">
            {{ getFieldTypeLabel(record.field_type) }}
          </a-tag>
        </template>
        <template v-if="column.key === 'is_active'">
          <a-tag :color="record.is_active ? 'green' : 'red'">
            {{ record.is_active ? '启用' : '禁用' }}
          </a-tag>
        </template>
        <template v-if="column.key === 'created_at'">
          <span v-if="record.created_at">{{ formatDateTime(record.created_at) }}</span>
          <span v-else>-</span>
        </template>
        <template v-if="column.key === 'action'">
          <a-space>
            <a-button v-permission="'post/api/v1/autofill/field_spec/update'" type="link" size="small"
              @click="handleEdit(record)">编辑</a-button>
            <a-popconfirm title="确定删除该字段吗？" @confirm="handleDelete(record)">
              <a-button v-permission="'delete/api/v1/autofill/field_spec/delete'" type="link" danger
                size="small">删除</a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </template>

      <!-- 弹窗表单 -->
      <template #modal-form="{ form }">
        <a-form-item v-if="userStore.isSuperUser" label="所属租户" name="tenant_id">
          <a-select v-model:value="form.tenant_id" placeholder="请选择租户" :options="tenantOptions"
            @change="(val: number) => handleModalTenantChange(val, form)" />
        </a-form-item>
        <a-form-item label="应用名称" name="app_name" required>
          <a-select v-model:value="form.app_name" placeholder="请选择应用" :options="appOptions" />
        </a-form-item>
        <a-form-item label="字段名" name="field_name">
          <a-input v-model:value="form.field_name" placeholder="请输入字段名（最多50个字符）" :disabled="modalAction === 'edit'" />
        </a-form-item>
        <a-form-item label="字段标签" name="field_label">
          <a-input v-model:value="form.field_label" placeholder="请输入字段显示名称" />
        </a-form-item>
        <a-form-item label="字段类型" name="field_type">
          <a-radio-group v-model:value="form.field_type" :disabled="modalAction === 'edit'">
            <a-radio value="text">文本输入</a-radio>
            <a-radio value="select_single">下拉单选</a-radio>
            <a-radio value="select_multi">下拉多选</a-radio>
            <a-radio value="template">模板类型</a-radio>
          </a-radio-group>
        </a-form-item>
        <a-form-item label="填写指引" name="fill_instruction">
          <a-textarea v-model:value="form.fill_instruction" placeholder="请输入字段填写指引，用于生成LLM描述" :rows="3" />
        </a-form-item>

        <!-- 模板类型配置 -->
        <template v-if="form.field_type === 'template'">
          <a-divider orientation="left">模板配置</a-divider>

          <!-- API配置 -->
          <a-divider orientation="left">API配置</a-divider>

          <!-- Header配置 -->
          <a-form-item label="请求Header">
            <div v-for="(header, index) in form.options.api_headers" :key="index" class="header-item">
              <a-space>
                <a-input v-model:value="header.key" placeholder="Header键" style="width: 150px" />
                <a-input v-model:value="header.value" placeholder="Header值" style="width: 250px" />
                <a-button type="link" danger @click="removeApiHeader(index)">
                  <DeleteOutlined />
                </a-button>
              </a-space>
            </div>
            <a-button type="dashed" block @click="addApiHeader">
              <PlusOutlined />
              添加Header
            </a-button>
          </a-form-item>

          <!-- Schema配置 -->
          <a-form-item label="模板API Schema">
            <a-textarea v-model:value="form.options.api_schema"
              placeholder="请输入模板API配置（YAML格式）&#10;&#10;支持以下扩展字段：&#10;1. x-api-params: 配置静态请求参数&#10;2. x-template-mapping: 配置模板字段映射（JSONPath语法）&#10;&#10;示例：&#10;paths:&#10;  /api/template/list:&#10;    get:&#10;      x-api-params:&#10;        headers:&#10;          Authorization: Bearer xxx&#10;      x-template-mapping:&#10;        template_name_path: '$.data[*].name'&#10;        template_content_path: '$.data[*].template_content'&#10;        group_name_pattern: '$.name + 服务记录'&#10;&#10;字段映射语法说明：&#10;  $.data[*].name              -> 从data数组中提取name字段作为模板名称&#10;  $.data[*].template_content  -> 从data数组中提取template_content字段作为模板内容&#10;  $.name + 服务记录          -> 字段组名称生成规则，使用JSONPath提取名称并拼接后缀"
              :rows="20" />
          </a-form-item>

          <!-- 解析提示词配置 -->
          <a-form-item label="解析提示词">
            <a-textarea v-model:value="form.options.parse_prompt"
              placeholder="请输入自定义的模板解析提示词（可选）&#10;&#10;留空将使用系统默认提示词。&#10;&#10;提示词中需要包含 {template_content} 占位符，系统会将模板内容替换到该位置。&#10;&#10;示例：&#10;你是一个专业的模板解析助手。请分析以下模板内容，提取关键信息字段。&#10;&#10;## 输入模板内容&#10;{template_content}&#10;&#10;## 解析要求&#10;1. 分析模板内容，识别所有需要填写的关键信息点&#10;2. 为每个关键信息提取字段..."
              :rows="15" />
            <a-typography-text type="secondary">
              自定义提示词将优先于默认提示词使用，用于控制LLM如何解析模板内容
            </a-typography-text>
          </a-form-item>

          <!-- 模板选择器配置 -->
          <a-divider orientation="left">模板选择器配置</a-divider>
          <a-form-item>
            <a-switch v-model:checked="form.options.enable_template_selector" />
            <span style="margin-left: 8px;">启用模板选择器字段</span>
            <a-typography-text type="secondary" style="margin-left: 16px;">
              同步时自动生成一个下拉字段，用于选择适用的模板
            </a-typography-text>
          </a-form-item>

          <template v-if="form.options.enable_template_selector">
            <a-row :gutter="16">
              <a-col :span="12">
                <a-form-item label="选择器字段名">
                  <a-input v-model:value="form.options.template_selector_field_name" placeholder="template_selector" />
                </a-form-item>
              </a-col>
              <a-col :span="12">
                <a-form-item label="选择器字段标签">
                  <a-input v-model:value="form.options.template_selector_field_label" placeholder="模板选择" />
                </a-form-item>
              </a-col>
            </a-row>
            <a-row :gutter="16">
              <a-col :span="12">
                <a-form-item label="选项标签路径">
                  <a-input v-model:value="form.options.template_selector_label_path" placeholder="$.name" />
                  <a-typography-text type="secondary">
                    JSONPath路径，用于从模板数据中提取选项显示标签
                  </a-typography-text>
                </a-form-item>
              </a-col>
              <a-col :span="12">
                <a-form-item label="选项值路径">
                  <a-input v-model:value="form.options.template_selector_value_path" placeholder="$.id" />
                  <a-typography-text type="secondary">
                    JSONPath路径，用于从模板数据中提取选项值
                  </a-typography-text>
                </a-form-item>
              </a-col>
            </a-row>
          </template>

          <!-- 导入按钮 -->
          <a-form-item>
            <a-space>
              <a-button type="primary" :loading="syncLoading" @click="handleSyncTemplate">
                <SyncOutlined />
                同步模板
              </a-button>
              <a-button @click="showTemplateCurlModal">
                <CodeOutlined />
                从 curl 导入
              </a-button>
              <a-button v-if="form.id" @click="handleViewSyncStatus">
                <EyeOutlined />
                查看同步状态
              </a-button>
            </a-space>
            <a-typography-text type="secondary" style="margin-left: 8px">
              根据Schema配置从API同步模板并生成字段组
            </a-typography-text>
          </a-form-item>

          <!-- 同步状态显示 -->
          <a-form-item v-if="syncStatusInfo.status">
            <a-alert :message="`同步状态: ${getSyncStatusText(syncStatusInfo.status)}`"
              :description="syncStatusInfo.message || syncStatusInfo.error_msg"
              :type="getSyncStatusType(syncStatusInfo.status)" show-icon />
            <div v-if="syncStatusInfo.details && syncStatusInfo.details.length > 0" style="margin-top: 8px;">
              <a-typography-text type="secondary">
                成功: {{ syncStatusInfo.success_count }} / {{ syncStatusInfo.total_count }}
              </a-typography-text>
            </div>
          </a-form-item>
        </template>

        <!-- 下拉单选/多选类型选项配置 -->
        <template v-if="form.field_type === 'select_single' || form.field_type === 'select_multi'">
          <a-divider orientation="left">选项配置</a-divider>

          <!-- 多选时显示选项数限制 -->
          <template v-if="form.field_type === 'select_multi'">
            <a-form-item label="选项数限制" class="selection-limit-item">
              <a-row :gutter="16">
                <a-col :span="12">
                  <div class="limit-input-wrapper">
                    <span class="limit-label">最少选择</span>
                    <a-input-number v-model:value="form.options.min_selections" :min="1"
                      :max="form.options.max_selections || 100" style="width: 100%" />
                  </div>
                </a-col>
                <a-col :span="12">
                  <div class="limit-input-wrapper">
                    <span class="limit-label">最多选择</span>
                    <a-input-number v-model:value="form.options.max_selections" :min="form.options.min_selections || 1"
                      :max="100" style="width: 100%" />
                  </div>
                </a-col>
              </a-row>
            </a-form-item>
          </template>

          <!-- API配置 -->
          <a-divider orientation="left">API配置</a-divider>

          <!-- Header配置 -->
          <a-form-item label="请求Header">
            <div v-for="(header, index) in form.options.api_headers" :key="index" class="header-item">
              <a-space>
                <a-input v-model:value="header.key" placeholder="Header键" style="width: 150px" />
                <a-input v-model:value="header.value" placeholder="Header值" style="width: 250px" />
                <a-button type="link" danger @click="removeApiHeader(index)">
                  <DeleteOutlined />
                </a-button>
              </a-space>
            </div>
            <a-button type="dashed" block @click="addApiHeader">
              <PlusOutlined />
              添加Header
            </a-button>
          </a-form-item>

          <!-- Schema配置 -->
          <a-form-item label="OpenAPI Schema">
            <a-textarea v-model:value="form.options.api_schema"
              placeholder="请输入OpenAPI/Swagger配置（YAML格式）&#10;&#10;支持以下扩展字段：&#10;1. x-api-params: 配置静态请求参数&#10;2. x-field-mapping: 配置字段映射（JSONPath语法）&#10;&#10;示例：&#10;paths:&#10;  /api/endpoint:&#10;    post:&#10;      x-api-params:&#10;        parent_id: 0&#10;        app_name: test_app&#10;        class_name: 400电话&#10;      x-field-mapping:&#10;        label_path: '$.data[*].summary'&#10;        value_path: '$.data[*].option_value'&#10;&#10;字段映射语法说明：&#10;  $.data[*].name     -> 从data数组中提取name字段&#10;  $.result[*].title  -> 从result数组中提取title字段&#10;  $.data[0].list[*]  -> 从data[0].list数组中提取元素&#10;&#10;默认映射（标准格式）：&#10;  label_path: '$.data[*].label'&#10;  value_path: '$.data[*].value'"
              :rows="15" />
          </a-form-item>

          <!-- 同步按钮 -->
          <a-form-item>
            <a-space>
              <a-button type="primary" :loading="syncLoading" @click="handleSyncOptions">
                <SyncOutlined />
                同步选项
              </a-button>
              <a-button @click="showCurlModal">
                <CodeOutlined />
                从 curl 导入
              </a-button>
            </a-space>
            <a-typography-text type="secondary" style="margin-left: 8px">
              根据Schema配置从API同步下拉选项
            </a-typography-text>
          </a-form-item>

          <!-- 级联配置 -->
          <a-divider orientation="left">级联配置</a-divider>

          <!-- 级联配置列表 -->
          <a-form-item v-if="fieldCascadeConfigs.length > 0">
            <a-list :data-source="fieldCascadeConfigs" item-layout="horizontal" size="small">
              <template #renderItem="{ item, index }">
                <a-list-item>
                  <template #actions>
                    <a-button type="link" size="small" @click="editCascadeConfig(item)">编辑</a-button>
                    <a-button type="link" size="small" :loading="item.syncing"
                      @click="syncCascadeConfig(item)">同步</a-button>
                    <a-popconfirm title="确定删除该级联配置吗？" @confirm="deleteCascadeConfig(item)">
                      <a-button type="link" danger size="small">删除</a-button>
                    </a-popconfirm>
                  </template>
                  <a-list-item-meta>
                    <template #title>级联配置 {{ index + 1 }}: {{ item.parent_field_name }} 子字段</template>
                    <template #description>
                      <a-tag color="blue">字段名规则: {{ item.field_name_pattern }}</a-tag>
                      <a-tag color="cyan">字段标签规则: {{ item.field_label_pattern }}</a-tag>
                      <br>
                      <span v-if="item.last_sync_at">
                        最后同步: {{ formatDateTime(item.last_sync_at) }}
                      </span>
                    </template>
                  </a-list-item-meta>
                </a-list-item>
              </template>
            </a-list>
          </a-form-item>

          <!-- 添加级联配置按钮（始终显示，支持多个） -->
          <a-form-item>
            <a-button type="dashed" block @click="showAddCascadeModal">
              <PlusOutlined />
              {{ fieldCascadeConfigs.length === 0 ? '添加级联子字段' : '添加更多级联子字段' }}
            </a-button>
          </a-form-item>

          <a-divider orientation="left">选项列表</a-divider>

          <a-form-item label="选项列表">
            <a-typography-text type="secondary" style="margin-bottom: 8px; display: block;">
              使用 Markdown 格式编辑选项，格式示例：<br>
              <code>## 选项标签</code> - 选项标题（人工识别）<br>
              <code>- 选项值:</code> 选项值（ID等）<br>
              <code>- 填写说明:</code> 填写说明内容（支持多行，续行缩进即可）<br>
              <code>- 批注:</code> 人工标注内容（可多个，也支持多行）
            </a-typography-text>
            <a-textarea v-model:value="optionsMarkdown" :rows="20"
              placeholder="## 智能网联&#10;- 选项值: 1001&#10;- 填写说明: 选择云控相关问题&#10;  第二行补充说明&#10;  第三行补充说明&#10;- 批注: 这是批注内容1&#10;- 批注: 这是批注内容2&#10;&#10;## 产品咨询&#10;- 选项值: 1002&#10;- 填写说明: 选择产品咨询类问题&#10;  可以有多行说明内容"
              @blur="parseMarkdownToOptions" />
          </a-form-item>
        </template>

        <!-- Text类型批注配置 -->
        <template v-if="form.field_type === 'text'">
          <a-divider orientation="left">全局批注</a-divider>
          <a-form-item label="批注列表">
            <div v-for="(item, index) in form.corrections" :key="index" class="correction-item">
              <a-space>
                <a-textarea v-model:value="item.text" placeholder="批注内容" :rows="2" style="width: 400px" />
                <a-button type="link" danger @click="removeCorrection(index)">
                  <DeleteOutlined />
                </a-button>
              </a-space>
            </div>
            <a-button type="dashed" block @click="addCorrection">
              <PlusOutlined />
              添加批注
            </a-button>
          </a-form-item>
        </template>

        <a-form-item label="状态" name="is_active">
          <a-switch v-model:checked="form.is_active" />
        </a-form-item>
      </template>
    </CrudTable>

    <!-- curl 解析弹窗 - 第一步：输入 curl 命令 -->
    <a-modal v-model:open="curlModalVisible" title="从 curl 命令导入 OpenAPI Schema" :confirm-loading="curlModalLoading"
      @ok="handleParseCurlStep1" @cancel="handleCancelCurlModal" width="700px">
      <a-form layout="vertical">
        <a-form-item label="curl 命令" required>
          <a-textarea v-model:value="curlForm.curl_command"
            placeholder="请输入 curl 命令，例如：&#10;curl -X POST http://localhost:9999/api/autofill/dropdown_options/list \\&#10;  -H 'Authorization: Bearer your_token' \\&#10;  -H 'Content-Type: application/json' \\&#10;  -d '{&quot;parent_id&quot;: 0}'"
            :rows="8" />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- curl 解析弹窗 - 第二步：配置 JSONPath 和展平 -->
    <a-modal v-model:open="curlConfigModalVisible" title="配置字段映射" :confirm-loading="curlConfigModalLoading"
      @ok="handleParseCurlStep2" @cancel="handleCancelCurlConfigModal" width="800px">
      <a-form layout="vertical">
        <a-form-item label="标签字段 JSONPath">
          <a-input v-model:value="curlForm.label_path" placeholder="$.data[*].label" />
        </a-form-item>
        <a-form-item label="值字段 JSONPath">
          <a-input v-model:value="curlForm.value_path" placeholder="$.data[*].value" />
        </a-form-item>

        <a-divider orientation="left">展平配置</a-divider>
        <a-form-item>
          <a-switch v-model:checked="curlForm.enable_flatten" @change="onCurlFlattenChange" />
          <span style="margin-left: 8px;">启用展平</span>
        </a-form-item>
        <template v-if="curlForm.enable_flatten">
          <a-row :gutter="16">
            <a-col :span="12">
              <a-form-item label="标签分隔符">
                <a-input v-model:value="curlForm.flatten_label_separator" placeholder="-" />
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="值分隔符">
                <a-input v-model:value="curlForm.flatten_value_separator" placeholder="-" />
              </a-form-item>
            </a-col>
          </a-row>
          <a-row :gutter="16">
            <a-col :span="12">
              <a-form-item label="标签路径2">
                <a-input v-model:value="curlForm.flatten_label_path2" placeholder="$.data[*].children[*].label" />
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="值路径2">
                <a-input v-model:value="curlForm.flatten_value_path2" placeholder="$.data[*].children[*].value" />
              </a-form-item>
            </a-col>
          </a-row>
          <a-row :gutter="16">
            <a-col :span="12">
              <a-form-item label="标签路径3">
                <a-input v-model:value="curlForm.flatten_label_path3"
                  placeholder="$.data[*].children[*].children[*].label" />
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="值路径3">
                <a-input v-model:value="curlForm.flatten_value_path3"
                  placeholder="$.data[*].children[*].children[*].value" />
              </a-form-item>
            </a-col>
          </a-row>
        </template>
      </a-form>
    </a-modal>

    <!-- 级联配置弹窗 -->
    <a-modal v-model:open="cascadeModalVisible" title="级联子字段配置" :confirm-loading="cascadeModalLoading"
      @ok="handleSaveCascadeConfig" @cancel="handleCancelCascadeModal" width="900px">
      <a-form layout="vertical">
        <a-form-item label="字段名规则">
          <a-input v-model:value="cascadeConfig.field_name_pattern" placeholder="parent.$.data[*].label + -的二三级" />
          <a-typography-text type="secondary">
            字段名规则：parent.$.data[*].label 表示父字段选项的标签值，+ 表示连接，-的二三级 为固定后缀
          </a-typography-text>
        </a-form-item>
        <a-form-item label="字段标签规则">
          <a-input v-model:value="cascadeConfig.field_label_pattern" placeholder="parent.$.data[*].value + -的二三级" />
          <a-typography-text type="secondary">
            字段标签规则：parent.$.data[*].value 表示父字段选项的值，+ 表示连接，-的二三级 为固定后缀。支持 parent.$.data[*].label 使用标签值
          </a-typography-text>
        </a-form-item>

        <a-divider orientation="left">API配置</a-divider>

        <!-- 动态参数配置 -->
        <a-form-item label="动态参数配置">
          <a-typography-text type="secondary" style="margin-bottom: 8px; display: block;">
            配置 x-api-params 中的动态参数，用于从父字段获取值。例如：first_level_value = parent.$.data[*].value
          </a-typography-text>
          <div v-for="(param, index) in cascadeConfig.dynamic_params" :key="index" class="header-item">
            <a-space>
              <a-input v-model:value="param.key" placeholder="参数名，如 first_level_value" style="width: 220px" />
              <span>=</span>
              <a-input v-model:value="param.value" placeholder="parent.$.data[*].value" style="width: 220px" />
              <a-button type="link" danger @click="removeDynamicParam(index)">
                <DeleteOutlined />
              </a-button>
            </a-space>
          </div>
          <a-button type="dashed" @click="addDynamicParam">
            <PlusOutlined />
            添加参数
          </a-button>
        </a-form-item>

        <a-form-item label="OpenAPI Schema">
          <a-textarea v-model:value="cascadeConfig.api_schema" :rows="12" />
        </a-form-item>
        <a-form-item>
          <a-button @click="showCascadeCurlModal">
            <CodeOutlined />
            从 curl 导入
          </a-button>
        </a-form-item>

      </a-form>
    </a-modal>

    <!-- 级联配置 curl 解析弹窗 - 第一步：输入 curl 命令 -->
    <a-modal v-model:open="cascadeCurlModalVisible" title="从 curl 命令导入 OpenAPI Schema"
      :confirm-loading="cascadeCurlModalLoading" @ok="handleParseCascadeCurlStep1"
      @cancel="handleCancelCascadeCurlModal" width="700px">
      <a-form layout="vertical">
        <a-form-item label="curl 命令" required>
          <a-textarea v-model:value="cascadeCurlForm.curl_command"
            placeholder="请输入 curl 命令，例如：&#10;curl -X POST 'http://localhost:9999/api/autofill/dropdown/submenus_tree' \\&#10;  -H 'Authorization: Bearer your_token' \\&#10;  -H 'Content-Type: application/json' \\&#10;  -d '{&quot;first_level_value&quot;: &quot;xxx&quot;}'"
            :rows="8" />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 级联配置 curl 解析弹窗 - 第二步：配置 JSONPath 和展平 -->
    <a-modal v-model:open="cascadeCurlConfigModalVisible" title="配置字段映射"
      :confirm-loading="cascadeCurlConfigModalLoading" @ok="handleParseCascadeCurlStep2"
      @cancel="handleCancelCascadeCurlConfigModal" width="800px">
      <a-form layout="vertical">
        <a-form-item label="标签字段 JSONPath">
          <a-input v-model:value="cascadeCurlForm.label_path" placeholder="$.data[*].label" />
        </a-form-item>
        <a-form-item label="值字段 JSONPath">
          <a-input v-model:value="cascadeCurlForm.value_path" placeholder="$.data[*].value" />
        </a-form-item>

        <a-divider orientation="left">展平配置</a-divider>
        <a-form-item>
          <a-switch v-model:checked="cascadeCurlForm.enable_flatten" @change="onCascadeCurlFlattenChange" />
          <span style="margin-left: 8px;">启用展平</span>
        </a-form-item>
        <template v-if="cascadeCurlForm.enable_flatten">
          <a-row :gutter="16">
            <a-col :span="12">
              <a-form-item label="标签分隔符">
                <a-input v-model:value="cascadeCurlForm.flatten_label_separator" placeholder="-" />
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="值分隔符">
                <a-input v-model:value="cascadeCurlForm.flatten_value_separator" placeholder="-" />
              </a-form-item>
            </a-col>
          </a-row>
          <a-row :gutter="16">
            <a-col :span="12">
              <a-form-item label="标签路径2">
                <a-input v-model:value="cascadeCurlForm.flatten_label_path2"
                  placeholder="$.data[*].children[*].label" />
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="值路径2">
                <a-input v-model:value="cascadeCurlForm.flatten_value_path2"
                  placeholder="$.data[*].children[*].value" />
              </a-form-item>
            </a-col>
          </a-row>
          <a-row :gutter="16">
            <a-col :span="12">
              <a-form-item label="标签路径3">
                <a-input v-model:value="cascadeCurlForm.flatten_label_path3"
                  placeholder="$.data[*].children[*].children[*].label" />
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="值路径3">
                <a-input v-model:value="cascadeCurlForm.flatten_value_path3"
                  placeholder="$.data[*].children[*].children[*].value" />
              </a-form-item>
            </a-col>
          </a-row>
        </template>
      </a-form>
    </a-modal>

    <!-- 模板类型 curl 解析弹窗 - 第一步：输入 curl 命令 -->
    <a-modal v-model:open="templateCurlModalVisible" title="从 curl 命令导入模板 API Schema"
      :confirm-loading="templateCurlModalLoading" @ok="handleParseTemplateCurlStep1"
      @cancel="handleCancelTemplateCurlModal" width="700px">
      <a-form layout="vertical">
        <a-form-item label="curl 命令" required>
          <a-textarea v-model:value="templateCurlForm.curl_command"
            placeholder="请输入 curl 命令，例如：&#10;curl -X GET 'http://localhost:3200/api/v1/autofill/template/list' \&#10;  -H 'Authorization: Bearer your_token' \&#10;  -H 'Content-Type: application/json'"
            :rows="8" />
        </a-form-item>
        <a-form-item label="模板名称字段 JSONPath">
          <a-input v-model:value="templateCurlForm.template_name_path" placeholder="$.items[*].name" />
        </a-form-item>
        <a-form-item label="模板内容字段 JSONPath">
          <a-input v-model:value="templateCurlForm.template_content_path" placeholder="$.items[*].template_content" />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 模板类型 curl 解析弹窗 - 第二步：配置字段映射 -->
    <a-modal v-model:open="templateCurlConfigModalVisible" title="配置模板字段映射"
      :confirm-loading="templateCurlConfigModalLoading" @ok="handleParseTemplateCurlStep2"
      @cancel="handleCancelTemplateCurlConfigModal" width="800px">
      <a-form layout="vertical">
        <a-form-item label="模板名称字段 JSONPath">
          <a-input v-model:value="templateCurlForm.template_name_path" placeholder="$.data[*].name" />
        </a-form-item>
        <a-form-item label="模板内容字段 JSONPath">
          <a-input v-model:value="templateCurlForm.template_content_path" placeholder="$.data[*].template_content" />
        </a-form-item>
        <a-form-item label="字段组名称规则">
          <a-input v-model:value="templateCurlForm.group_name_pattern" placeholder="$.data[*].name + 的服务记录" />
          <a-typography-text type="secondary">
            格式：$.data[*].name + 的服务记录，+ 前为JSONPath表达式，+ 后为固定后缀
          </a-typography-text>
        </a-form-item>
        <a-form-item label="模板解析 Prompt">
          <a-textarea v-model:value="templateCurlForm.parse_prompt" placeholder="请输入用于解析模板内容的 Prompt" :rows="6" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import api from '@/api'
import CrudTable from '@/components/CrudTable/index.vue'
import { useUserStore } from '@/store'
import { formatDateTime } from '@/utils'
import { CodeOutlined, DeleteOutlined, ExportOutlined, ImportOutlined, PlusOutlined, SyncOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import * as yaml from 'js-yaml'
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'

// 默认模板解析提示词
const DEFAULT_PARSE_PROMPT = `# 任务：车企售后服务记录模板标准化 + 字段元数据批量提取

## 输出要求
1. 仅输出标准JSON格式，无任何额外文字、解释、标题、分隔线
2. 严格遵守以下JSON结构，不得新增或缺失字段
3. 布尔值使用小写true/false，不得使用字符串"true"/"false"
4. 所有字符串使用双引号包裹，转义内部双引号

## 第一部分：模板标准化规则
1. 保留原文所有固定业务话术、行文逻辑、句式顺序
2. 将所有可变填写内容替换为标准占位符：\${field_name}
3. 删除所有人工操作提示、括号内冗余备注、内部指引性文字
4. 保留固定枚举选项的描述，仅将填空位置替换为占位符

## 第二部分：字段提取规则
从原始模板中提取每个可变字段，包含以下属性：
- field_name：字段英文标识（小写下划线，用于占位符和JSON输出）
- field_label：字段中文展示名称
- fill_instruction：整合模板内所有约束信息，包括：字段含义、填写格式、数据类型、可选范围、数值标准、必填要求
- is_required：是否必填，从原文"必填"标注判断，布尔值

## 第三部分：模板填写规则提取
分析模板内容，提取该模板的适用场景和填写规则，包括：
- 该模板适用于什么类型的服务记录场景
- 使用该模板需要满足什么条件
- 模板的主要填写内容和关键信息点
- 模板的使用注意事项

## 输出JSON结构
{
  "standardized_template": "标准化后的完整模板，使用\${field_name}占位符",
  "template_rules": "该模板的填写规则和使用指引，包括适用场景、填写要求、注意事项等",
  "fields": [
    {
      "field_name": "customer_name",
      "field_label": "客户姓名",
      "fill_instruction": "填写车主姓名及称呼，文本类型",
      "is_required": true
    }
  ]
}

## 输入模板内容
{template_content}`

interface Props {
  fieldGroupId?: number
  fieldGroupName?: string
}

const props = withDefaults(defineProps<Props>(), {
  fieldGroupId: undefined,
  fieldGroupName: '',
})

const emit = defineEmits<{
  close: []
}>()

defineOptions({ name: 'FieldSpecManagement' })

const userStore = useUserStore()
const crudTableRef = ref<InstanceType<typeof CrudTable>>()

// 查询参数
const queryParams = reactive({
  field_name: '',
  field_label: '',
  field_type: undefined as string | undefined,
  app_name: undefined as string | undefined,
  tenant_id: undefined as number | undefined,
})

// 租户选项
const tenantOptions = ref<{ label: string; value: number }[]>([])

// 应用选项
const appOptions = ref<{ label: string; value: string }[]>([])

// 表格数据
const loading = ref(false)
const tableData = ref<any[]>([])
const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
})

// 多选相关
const selectedRowKeys = ref<number[]>([])
const selectedRows = ref<any[]>([])

// 行选择配置
const rowSelection = computed(() => ({
  type: 'checkbox' as const,
  selectedRowKeys: selectedRowKeys.value,
  onChange: (keys: number[], rows: any[]) => {
    selectedRowKeys.value = keys
    selectedRows.value = rows
  },
  preserveSelectedRowKeys: true,
}))

// 弹窗数据
const modalTitle = ref('')
const modalLoading = ref(false)
const modalAction = ref<'add' | 'edit'>('add')
const syncLoading = ref(false)

// 同步状态信息
const syncStatusInfo = reactive({
  status: '',
  message: '',
  error_msg: '',
  total_count: 0,
  success_count: 0,
  failed_count: 0,
  details: []
})

// 获取同步状态文本
const getSyncStatusText = (status: string) => {
  const statusMap: Record<string, string> = {
    'pending': '等待中',
    'running': '同步中',
    'success': '同步成功',
    'failed': '同步失败',
    'partial': '部分成功'
  }
  return statusMap[status] || status
}

// 获取同步状态类型（用于alert组件）
const getSyncStatusType = (status: string): 'success' | 'error' | 'warning' | 'info' => {
  const typeMap: Record<string, 'success' | 'error' | 'warning' | 'info'> = {
    'pending': 'info',
    'running': 'info',
    'success': 'success',
    'failed': 'error',
    'partial': 'warning'
  }
  return typeMap[status] || 'info'
}

// 查看同步状态
const handleViewSyncStatus = async () => {
  if (!modalForm.id) {
    message.warning('请先保存字段')
    return
  }

  try {
    const res: any = await api.getFieldSpecSyncStatus({
      field_spec_id: modalForm.id
    })
    if (res.code === 200) {
      Object.assign(syncStatusInfo, res.data)
      message.success('同步状态已更新')
    } else {
      message.error(res.msg || '获取同步状态失败')
    }
  } catch (error: any) {
    message.error(error.message || '获取同步状态失败')
  }
}

// curl 解析弹窗数据
const curlModalVisible = ref(false)
const curlModalLoading = ref(false)
const curlConfigModalVisible = ref(false)
const curlConfigModalLoading = ref(false)
const curlForm = reactive({
  curl_command: '',
  label_path: '$.data[*].label',
  value_path: '$.data[*].value',
  enable_flatten: false,
  flatten_label_path2: '$.data[*].children[*].label',
  flatten_label_path3: '$.data[*].children[*].children[*].label',
  flatten_label_separator: '-',
  flatten_value_path2: '$.data[*].children[*].value',
  flatten_value_path3: '$.data[*].children[*].children[*].value',
  flatten_value_separator: '-',
  // 临时存储解析后的 schema
  parsed_schema: '',
})

// 级联配置弹窗数据
const cascadeModalVisible = ref(false)
const cascadeModalLoading = ref(false)
const cascadeConfig = reactive({
  id: undefined as number | undefined,
  parent_field_id: undefined as number | undefined,
  field_name_pattern: 'parent.$.data[*].label + -的二三级',
  field_label_pattern: 'parent.$.data[*].label + -的二三级',
  dynamic_params: [] as { key: string; value: string }[],
  api_schema: '',
})

// 级联配置 curl 解析弹窗数据
const cascadeCurlModalVisible = ref(false)
const cascadeCurlModalLoading = ref(false)
const cascadeCurlConfigModalVisible = ref(false)
const cascadeCurlConfigModalLoading = ref(false)
const cascadeCurlForm = reactive({
  curl_command: '',
  label_path: '$.data[*].label',
  value_path: '$.data[*].value',
  enable_flatten: false,
  flatten_label_path2: '$.data[*].children[*].label',
  flatten_label_path3: '$.data[*].children[*].children[*].label',
  flatten_label_separator: '-',
  flatten_value_path2: '$.data[*].children[*].value',
  flatten_value_path3: '$.data[*].children[*].children[*].value',
  flatten_value_separator: '-',
  // 临时存储解析后的 schema
  parsed_schema: '',
})

// 默认的 LLM 模板解析 Prompt
const DEFAULT_TEMPLATE_PARSE_PROMPT = '你是一个专业的模板解析助手。请分析以下模板内容，提取关键信息字段。\n\n' +
  '## 输入模板内容\n' +
  '{template_content}\n\n' +
  '## 解析要求\n' +
  '1. 分析模板内容，识别所有需要填写的关键信息点\n' +
  '2. 提取所有字段，为每个字段输出：\n' +
  '   - field_name: 字段英文名（小写，下划线连接）\n' +
  '   - field_label: 字段中文标签（清晰易懂的中文名称）\n' +
  '   - fill_instruction: 填写指引（必须包含以下所有约束信息，从模板中提取）\n' +
  '3. 识别模板中的关键信息点，如：联系人、联系方式、地址、时间、状态等\n' +
  '4. 分析模板的适用场景和填写规则，生成 template_rules\n\n' +
  '## fill_instruction 填写指引提取规范\n' +
  'fill_instruction 必须整合模板中该字段的所有约束信息，包括但不限于：\n' +
  '1. **字段含义**：该字段代表什么业务含义\n' +
  '2. **填写格式**：如日期格式(YYYY-MM-DD)、手机号格式(11位)、身份证号格式(18位)等\n' +
  '3. **数据类型**：如字符串、数字、日期、布尔值等\n' +
  '4. **可选范围**：如是/否选项、特定枚举值（如：高中低、优良好差）\n' +
  '5. **数值标准**：如最小值、最大值、精度要求、单位（元/千克/公里等）\n' +
  '6. **必填要求**：是否必须填写\n' +
  '7. **示例值**：从模板中提取的具体示例\n' +
  '8. **特殊规则**：如只能输入数字、不能包含特殊字符、长度限制等\n\n' +
  '## template_rules 模板填写规则提取规范\n' +
  'template_rules 必须包含该模板的完整使用指引，包括：\n' +
  '1. **适用场景**：该模板适用于什么类型的服务记录场景\n' +
  '2. **使用条件**：使用该模板需要满足什么条件\n' +
  '3. **主要填写内容**：模板的主要填写内容和关键信息点\n' +
  '4. **使用注意事项**：模板的使用注意事项和特殊要求\n\n' +
  '## 输出格式（JSON）\n' +
  '{\n' +
  '    "standard_template": "车主姓名: ${customer_name}\\n联系电话: ${contact_phone}\\n服务类型: ${service_type}",\n' +
  '    "template_rules": "该模板适用于xxx场景，需要填写客户基本信息、服务类型等。使用时需注意xxx。",\n' +
  '    "fields": [\n' +
  '        {\n' +
  '            "field_name": "customer_name",\n' +
  '            "field_label": "车主姓名",\n' +
  '            "fill_instruction": "客户姓名，字符串类型，如：张先生、李女士。必填。"\n' +
  '        },\n' +
  '        {\n' +
  '            "field_name": "contact_phone",\n' +
  '            "field_label": "联系电话",\n' +
  '            "fill_instruction": "客户联系电话，11位手机号码，数字格式。必填。"\n' +
  '        },\n' +
  '        {\n' +
  '            "field_name": "service_type",\n' +
  '            "field_label": "服务类型",\n' +
  '            "fill_instruction": "服务类型，如：道路救援、保养预约、维修服务。必填。"\n' +
  '        }\n' +
  '    ]\n' +
  '}\n\n' +
  '## 重要说明\n' +
  '1. standard_template 必须是一个字符串，格式为：字段标签: ${field_name}，每个字段占一行，用 \\n 分隔\n' +
  '2. 示例格式："车主姓名: ${customer_name}\\n联系电话: ${contact_phone}\\n地址: ${address}"\n' +
  '3. 根据实际提取的字段生成对应的 standard_template，不要照搬示例\n' +
  '4. 字段名使用英文小写，下划线连接\n' +
  '5. 字段标签使用中文，清晰易懂\n' +
  '6. **fill_instruction 必须全面**：整合字段含义、格式、类型、范围、标准、必填要求等所有约束信息\n' +
  '7. **template_rules 必须详细**：包含适用场景、使用条件、主要填写内容、使用注意事项\n' +
  '8. 只返回JSON，不要包含任何解释说明'

// 模板类型 curl 解析弹窗数据
const templateCurlModalVisible = ref(false)
const templateCurlModalLoading = ref(false)
const templateCurlConfigModalVisible = ref(false)
const templateCurlConfigModalLoading = ref(false)
const templateCurlForm = reactive({
  curl_command: '',
  template_name_path: '$.data[*].name',
  template_content_path: '$.data[*].template_content',
  group_name_pattern: '$.data[*].name + 的服务记录',
  parse_prompt: DEFAULT_TEMPLATE_PARSE_PROMPT,
  // 临时存储解析后的 schema
  parsed_schema: '',
})

// 当前字段关联的级联配置
const fieldCascadeConfigs = ref<any[]>([])

const modalForm = reactive({
  id: undefined as number | undefined,
  tenant_id: undefined as number | undefined,
  app_name: undefined as string | undefined,
  field_name: '',
  field_label: '',
  field_type: 'text',
  fill_instruction: '',
  options: {
    items: [] as any[],
    min_selections: 1,
    max_selections: 0,  // 0表示无限制
    api_headers: [] as { key: string; value: string }[],
    api_schema: '',
    parse_prompt: '',
    // 模板选择器配置
    enable_template_selector: false,
    template_selector_field_name: 'template_selector',
    template_selector_field_label: '模板选择',
    template_selector_label_path: '$.name',
    template_selector_value_path: '$.id',
  },
  corrections: [] as any[],
  is_active: true,
})

// Markdown 格式的选项列表
const optionsMarkdown = ref('')

// 将选项数据转换为 Markdown 格式（支持多行填写说明）
const convertOptionsToMarkdown = (items: any[]): string => {
  if (!items || items.length === 0) return ''

  return items.map((item, index) => {
    const lines: string[] = []

    // 选项标签作为二级标题（人工识别）
    lines.push(`## ${item.label || ''}`)

    // 选项值
    if (item.value) {
      lines.push(`- 选项值: ${item.value}`)
    }

    // 填写说明（支持多行，使用缩进表示续行）
    if (item.fill_instruction) {
      const instructionLines = item.fill_instruction.split('\n')
      if (instructionLines.length === 1) {
        // 单行直接输出
        lines.push(`- 填写说明: ${item.fill_instruction}`)
      } else {
        // 多行使用缩进格式
        lines.push(`- 填写说明: ${instructionLines[0]}`)
        for (let i = 1; i < instructionLines.length; i++) {
          // 非空行添加缩进，空行保持空
          if (instructionLines[i].trim()) {
            lines.push(`  ${instructionLines[i]}`)
          } else {
            lines.push('')
          }
        }
      }
    }

    // 人工标注（可能有多个，每个批注也支持多行）
    if (item.corrections && item.corrections.length > 0) {
      item.corrections.forEach((corr: any) => {
        if (corr.text) {
          const corrLines = corr.text.split('\n')
          if (corrLines.length === 1) {
            lines.push(`- 批注: ${corr.text}`)
          } else {
            lines.push(`- 批注: ${corrLines[0]}`)
            for (let i = 1; i < corrLines.length; i++) {
              if (corrLines[i].trim()) {
                lines.push(`  ${corrLines[i]}`)
              } else {
                lines.push('')
              }
            }
          }
        }
      })
    }

    // 选项之间添加空行（最后一个除外）
    if (index < items.length - 1) {
      lines.push('')
    }

    return lines.join('\n')
  }).join('\n')
}

// 将 Markdown 格式解析为选项数据（支持多行填写说明和批注）
const parseMarkdownToOptions = () => {
  const markdown = optionsMarkdown.value.trim()
  if (!markdown) {
    modalForm.options.items = []
    return
  }

  const items: any[] = []
  const lines = markdown.split('\n')
  let currentItem: any = null
  let currentField: string | null = null // 当前正在解析的字段：'fill_instruction' | 'correction'
  let currentCorrectionIndex: number = -1

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    const trimmedLine = line.trim()

    // 空行处理：如果是续行模式，保留换行
    if (!trimmedLine) {
      if (currentField === 'fill_instruction' && currentItem) {
        currentItem.fill_instruction += '\n'
      } else if (currentField === 'correction' && currentItem && currentCorrectionIndex >= 0) {
        currentItem.corrections[currentCorrectionIndex].text += '\n'
      }
      continue
    }

    // 匹配二级标题 ## 选项标签
    const headerMatch = trimmedLine.match(/^##\s*(.+)$/)
    if (headerMatch) {
      // 保存上一个选项
      if (currentItem) {
        // 清理末尾的换行符
        if (currentItem.fill_instruction) {
          currentItem.fill_instruction = currentItem.fill_instruction.trimEnd()
        }
        currentItem.corrections.forEach((corr: any) => {
          if (corr.text) corr.text = corr.text.trimEnd()
        })
        items.push(currentItem)
      }
      // 重置状态
      currentField = null
      currentCorrectionIndex = -1
      // 创建新选项
      currentItem = {
        label: headerMatch[1].trim(),
        value: '',
        fill_instruction: '',
        corrections: [],
        is_deleted: false,
      }
      continue
    }

    // 如果没有当前选项，跳过
    if (!currentItem) continue

    // 检查是否是新的字段行（以 - 开头）
    const isNewField = line.match(/^-\s*/)

    // 如果不是新字段行，且处于续行模式，则追加内容
    if (!isNewField && currentField) {
      // 检查是否是缩进续行（以空格开头）
      const isIndented = line.match(/^\s+/)
      const content = isIndented ? line.trimStart() : trimmedLine

      if (currentField === 'fill_instruction') {
        currentItem.fill_instruction += '\n' + content
      } else if (currentField === 'correction' && currentCorrectionIndex >= 0) {
        currentItem.corrections[currentCorrectionIndex].text += '\n' + content
      }
      continue
    }

    // 匹配 - 选项值: xxx
    const valueMatch = trimmedLine.match(/^-\s*选项值[:：]\s*(.*)$/i)
    if (valueMatch) {
      currentField = null
      currentItem.value = valueMatch[1].trim()
      continue
    }

    // 匹配 - 填写说明: xxx
    const instructionMatch = trimmedLine.match(/^-\s*填写说明[:：]\s*(.*)$/i)
    if (instructionMatch) {
      currentField = 'fill_instruction'
      currentItem.fill_instruction = instructionMatch[1].trim()
      continue
    }

    // 匹配 - 批注: xxx
    const correctionMatch = trimmedLine.match(/^-\s*批注[:：]\s*(.*)$/i)
    if (correctionMatch) {
      currentField = 'correction'
      currentCorrectionIndex = currentItem.corrections.length
      currentItem.corrections.push({
        text: correctionMatch[1].trim(),
      })
      continue
    }
  }

  // 保存最后一个选项
  if (currentItem) {
    // 清理末尾的换行符
    if (currentItem.fill_instruction) {
      currentItem.fill_instruction = currentItem.fill_instruction.trimEnd()
    }
    currentItem.corrections.forEach((corr: any) => {
      if (corr.text) corr.text = corr.text.trimEnd()
    })
    items.push(currentItem)
  }

  modalForm.options.items = items
}

// 选项数据 - 新的字段类型：文本输入、下拉单选、下拉多选、模板类型
const fieldTypeOptions = [
  { label: '文本输入', value: 'text' },
  { label: '下拉单选', value: 'select_single' },
  { label: '下拉多选', value: 'select_multi' },
  { label: '模板类型', value: 'template' },
]

// 获取字段类型标签
const getFieldTypeLabel = (type: string) => {
  const option = fieldTypeOptions.find(opt => opt.value === type)
  return option?.label || type
}

// 获取字段类型颜色
const getFieldTypeColor = (type: string) => {
  switch (type) {
    case 'text': return 'green'
    case 'select_single': return 'blue'
    case 'select_multi': return 'orange'
    case 'template': return 'purple'
    default: return 'default'
  }
}
const fieldGroupOptions = ref<{ label: string; value: number }[]>([])
const allFieldGroups = ref<any[]>([]) // 存储所有字段组用于级联筛选

// 计算属性
const columns = computed(() => [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 80 },
  { title: '字段名', dataIndex: 'field_name', key: 'field_name' },
  { title: '字段标签', dataIndex: 'field_label', key: 'field_label' },
  { title: '字段类型', key: 'field_type', width: 120 },
  { title: '状态', key: 'is_active', width: 100 },
  { title: '创建时间', key: 'created_at', width: 180 },
  { title: '操作', key: 'action', width: 150, fixed: 'right' },
])

const filterItemCount = computed(() => userStore.isSuperUser ? 5 : 4)

const modalRules = computed(() => {
  const rules: any = {
    app_name: [
      { required: true, message: '请选择应用名称', trigger: 'change' },
    ],
    field_name: [
      { required: true, message: '请输入字段名', trigger: 'blur' },
      { max: 50, message: '字段名最多50个字符', trigger: 'blur' },
    ],
    field_label: [
      { required: true, message: '请输入字段标签', trigger: 'blur' },
    ],
    field_type: [
      { required: true, message: '请选择字段类型', trigger: 'change' },
    ],
  }
  // 超管必须选择所属租户
  if (userStore.isSuperUser) {
    rules.tenant_id = [
      { required: true, message: '请选择所属租户', trigger: 'change', type: 'number' },
    ]
  }
  return rules
})

// 方法
// 加载数据
const fetchData = async () => {
  loading.value = true
  try {
    const params: any = {
      page: pagination.current,
      page_size: pagination.pageSize,
      field_name: queryParams.field_name,
      field_label: queryParams.field_label,
      field_type: queryParams.field_type,
    }
    if (queryParams.app_name) {
      params.app_name = queryParams.app_name
    }
    // 超管可以按租户筛选
    if (userStore.isSuperUser && queryParams.tenant_id) {
      params.tenant_id = queryParams.tenant_id
    }
    const res: any = await api.getFieldSpecList(params)
    if (res.code === 200) {
      tableData.value = res.data || []
      pagination.total = res.total || 0
    }
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  pagination.current = 1
  fetchData()
}

const handleReset = () => {
  queryParams.field_name = ''
  queryParams.field_label = ''
  queryParams.field_type = undefined
  queryParams.app_name = undefined
  if (userStore.isSuperUser) {
    queryParams.tenant_id = undefined
  }
  pagination.current = 1
  fetchData()
}

// 加载字段组列表
const fetchFieldGroups = async (tenantId?: number) => {
  try {
    const params: any = { page_size: 1000 }
    // 如果指定了租户，只加载该租户的字段组
    if (tenantId && tenantId > 0) {
      params.tenant_id = tenantId
    }
    const res: any = await api.getFieldGroupList(params)
    if (res.code === 200) {
      allFieldGroups.value = res.data || []
      fieldGroupOptions.value = allFieldGroups.value.map((item: any) => ({
        label: `${item.group_name} (${item.group_code})`,
        value: item.id,
      }))
    }
  } catch (error) {
    console.error('加载字段组列表失败', error)
  }
}

// 加载租户列表
const fetchTenantOptions = async () => {
  if (!userStore.isSuperUser) return
  try {
    const res: any = await api.getTenantSelect()
    if (res.code === 200) {
      tenantOptions.value = (res.data || []).map((t: any) => ({
        label: t.name,
        value: t.id,
      }))
    }
  } catch (error) {
    console.error('获取租户列表失败', error)
  }
}

// 加载应用列表
const fetchAppOptions = async (tenantId?: number) => {
  try {
    const params: any = {}
    // 如果指定了租户（大于0），只加载该租户的应用
    if (tenantId && tenantId > 0) {
      params.tenant_id = tenantId
    }
    const res: any = await api.getAppSelect(params)
    if (res.code === 200) {
      appOptions.value = (res.data || []).map((app: any) => ({
        label: app.label,
        value: app.value,
      }))
    }
  } catch (error) {
    console.error('获取应用列表失败:', error)
  }
}

// 租户变更处理（筛选区域）
const handleTenantChange = (tenantId: number) => {
  // 清空应用选择
  queryParams.app_name = undefined
  // 重新加载该租户的应用列表
  fetchAppOptions(tenantId)
  // 刷新数据
  handleSearch()
}

// 弹窗中租户变更处理
const handleModalTenantChange = (tenantId: number, form: any) => {
  // 清空应用选择
  form.app_name = undefined
  // 重新加载该租户的应用列表
  fetchAppOptions(tenantId)
}

const handleTableChange = (pag: any) => {
  pagination.current = pag.current
  pagination.pageSize = pag.pageSize
  fetchData()
}

const resetModalForm = () => {
  modalForm.id = undefined
  modalForm.app_name = undefined
  modalForm.field_name = ''
  modalForm.field_label = ''
  modalForm.field_type = 'text'
  modalForm.fill_instruction = ''
  modalForm.tenant_id = userStore.isSuperUser ? undefined : userStore.userInfo?.current_tenant_id
  modalForm.options = {
    items: [],
    min_selections: 1,
    max_selections: 0,  // 0表示无限制
    api_headers: [],
    api_schema: '',
    parse_prompt: DEFAULT_PARSE_PROMPT,
    // 模板选择器配置
    enable_template_selector: false,
    template_selector_field_name: 'template_selector',
    template_selector_field_label: '模板选择',
    template_selector_label_path: '$.name',
    template_selector_value_path: '$.id',
  }
  modalForm.corrections = []
  modalForm.is_active = true
  optionsMarkdown.value = ''
}

const handleAdd = () => {
  modalAction.value = 'add'
  modalTitle.value = '新建字段'
  resetModalForm()
  crudTableRef.value?.openAddModal()
}

const handleEdit = (record: any) => {
  modalAction.value = 'edit'
  modalTitle.value = '编辑字段'
  modalForm.id = record.id
  modalForm.app_name = record.app_name
  modalForm.field_name = record.field_name
  modalForm.field_label = record.field_label
  modalForm.field_type = record.field_type
  modalForm.fill_instruction = record.fill_instruction || ''
  modalForm.tenant_id = record.tenant_id
  modalForm.options = {
    items: record.options?.items || [],
    min_selections: record.options?.min_selections ?? 1,
    max_selections: record.options?.max_selections ?? 0,  // 0表示无限制
    api_headers: record.options?.api_headers || [],
    api_schema: record.options?.api_schema || '',
    parse_prompt: record.options?.parse_prompt || '',
    // 模板选择器配置
    enable_template_selector: record.options?.enable_template_selector ?? false,
    template_selector_field_name: record.options?.template_selector_field_name || 'template_selector',
    template_selector_field_label: record.options?.template_selector_field_label || '模板选择',
    template_selector_label_path: record.options?.template_selector_label_path || '$.name',
    template_selector_value_path: record.options?.template_selector_value_path || '$.id',
  }
  modalForm.is_active = record.is_active
  // 将选项数据转换为 Markdown 格式
  optionsMarkdown.value = convertOptionsToMarkdown(record.options?.items || [])
  crudTableRef.value?.openEditModal(record)
  // 确保 corrections 是数组，避免 null 导致的问题（必须在 openEditModal 之后执行，因为 openEditModal 内部会 Object.assign 覆盖值）
  // 由于 Object.assign 会将 null 直接赋值给 corrections，我们需要重新赋值为数组
  const corrections = Array.isArray(record.corrections) ? record.corrections : []
    ; (modalForm as any).corrections = [...corrections]

  // 加载级联配置
  if (record.field_type === 'select_single' && record.id) {
    fetchFieldCascadeConfigs(record.id)
  } else {
    fieldCascadeConfigs.value = []
  }
}



const addCorrection = () => {
  modalForm.corrections.push({
    id: Date.now().toString(),
    text: '',
    created_by: userStore.userInfo?.username || 'system',
    created_at: new Date().toISOString(),
  })
}

const removeCorrection = (index: number) => {
  modalForm.corrections.splice(index, 1)
}

// API Header 相关方法
const addApiHeader = () => {
  if (!modalForm.options.api_headers) {
    modalForm.options.api_headers = []
  }
  modalForm.options.api_headers.push({ key: '', value: '' })
}

const removeApiHeader = (index: number) => {
  if (modalForm.options.api_headers) {
    modalForm.options.api_headers.splice(index, 1)
  }
}

// 同步选项方法
const handleSyncOptions = async () => {
  if (!modalForm.options.api_schema) {
    message.warning('请先配置OpenAPI Schema')
    return
  }

  // 验证必填字段
  if (!modalForm.field_name) {
    message.warning('请先填写字段名称')
    return
  }
  if (!modalForm.field_label) {
    message.warning('请先填写字段标签')
    return
  }

  syncLoading.value = true
  try {
    const res: any = await api.syncFieldSpecOptions({
      field_id: modalForm.id,
      field_name: modalForm.field_name,
      field_label: modalForm.field_label,
      field_type: modalForm.field_type,
      fill_instruction: modalForm.fill_instruction || '',
      options: modalForm.options,
    })
    if (res.code === 200) {
      // 更新选项列表
      modalForm.options.items = res.data.items || []
      // 同步成功后，将选项数据转换为 Markdown 格式
      optionsMarkdown.value = convertOptionsToMarkdown(res.data.items || [])
      // 更新字段ID（如果是新建）
      if (res.data.field_id && !modalForm.id) {
        modalForm.id = res.data.field_id
      }
      message.success(`同步成功，共更新 ${res.data.updated_count || 0} 个选项`)
    } else {
      message.error(res.msg || '同步失败')
    }
  } catch (error: any) {
    message.error(error.message || '同步失败')
  } finally {
    syncLoading.value = false
  }
}

// 同步模板方法
const handleSyncTemplate = async () => {
  // 验证必填字段
  if (!modalForm.id) {
    message.warning('请先保存字段，再执行同步')
    return
  }
  if (!modalForm.options.api_schema) {
    message.warning('请先配置模板API Schema')
    return
  }

  syncLoading.value = true
  try {
    const res: any = await api.syncFieldSpec({
      field_spec_id: modalForm.id,
    })
    if (res.code === 200) {
      message.success('同步任务已提交，请稍后查看同步状态')
    } else {
      message.error(res.msg || '同步失败')
    }
  } catch (error: any) {
    message.error(error.message || '同步失败')
  } finally {
    syncLoading.value = false
  }
}

// curl 解析相关方法
const showCurlModal = () => {
  curlForm.curl_command = ''
  curlForm.label_path = '$.data[*].label'
  curlForm.value_path = '$.data[*].value'
  curlForm.enable_flatten = false
  curlForm.parsed_schema = ''
  curlModalVisible.value = true
}

// 第一步：解析 curl 命令为 YAML
const handleParseCurlStep1 = async () => {
  if (!curlForm.curl_command.trim()) {
    message.warning('请输入 curl 命令')
    return
  }

  curlModalLoading.value = true
  try {
    const res: any = await api.parseCurlCommand({
      curl_command: curlForm.curl_command,
      // 第一步不传 label_path 和 value_path，只解析 curl 为 YAML
    })
    if (res.code === 200) {
      // 临时存储解析后的 schema
      curlForm.parsed_schema = res.data.openapi_schema
      message.success('curl 解析成功，请配置字段映射')
      curlModalVisible.value = false
      curlConfigModalVisible.value = true
    } else {
      message.error(res.msg || '解析失败')
    }
  } catch (error: any) {
    message.error(error.message || '解析失败')
  } finally {
    curlModalLoading.value = false
  }
}

// 第二步：应用 JSONPath 和展平配置
const handleParseCurlStep2 = async () => {
  if (!curlForm.parsed_schema) {
    message.warning('请先解析 curl 命令')
    return
  }

  curlConfigModalLoading.value = true
  try {
    const res: any = await api.applyFieldMapping({
      openapi_schema: curlForm.parsed_schema,
      label_path: curlForm.label_path,
      value_path: curlForm.value_path,
      enable_flatten: curlForm.enable_flatten,
      flatten_config: curlForm.enable_flatten ? {
        label_path_level2: curlForm.flatten_label_path2,
        label_path_level3: curlForm.flatten_label_path3,
        label_separator: curlForm.flatten_label_separator,
        value_path_level2: curlForm.flatten_value_path2,
        value_path_level3: curlForm.flatten_value_path3,
        value_separator: curlForm.flatten_value_separator,
      } : undefined,
    })
    if (res.code === 200) {
      // 将生成的 Schema 填入表单
      modalForm.options.api_schema = res.data.openapi_schema
      message.success('字段映射配置成功，已生成 OpenAPI Schema')
      curlConfigModalVisible.value = false
    } else {
      message.error(res.msg || '配置失败')
    }
  } catch (error: any) {
    message.error(error.message || '配置失败')
  } finally {
    curlConfigModalLoading.value = false
  }
}

const handleCancelCurlModal = () => {
  curlModalVisible.value = false
}

const handleCancelCurlConfigModal = () => {
  curlConfigModalVisible.value = false
}

// 模板类型 curl 解析相关方法
const showTemplateCurlModal = () => {
  templateCurlForm.curl_command = ''
  templateCurlForm.template_name_path = '$.data[*].name'
  templateCurlForm.template_content_path = '$.data[*].template_content'
  templateCurlForm.group_name_pattern = '$.data[*].name + 的服务记录'
  templateCurlForm.parse_prompt = DEFAULT_TEMPLATE_PARSE_PROMPT
  templateCurlForm.parsed_schema = ''
  templateCurlModalVisible.value = true
}

// 第一步：解析模板类型 curl 命令为 YAML
const handleParseTemplateCurlStep1 = async () => {
  if (!templateCurlForm.curl_command.trim()) {
    message.warning('请输入 curl 命令')
    return
  }

  templateCurlModalLoading.value = true
  try {
    const res: any = await api.parseTemplateCurl({
      curl_command: templateCurlForm.curl_command,
      template_name_path: templateCurlForm.template_name_path,
      template_content_path: templateCurlForm.template_content_path,
    })
    if (res.code === 200) {
      // 临时存储解析后的 schema
      templateCurlForm.parsed_schema = res.data.openapi_schema
      message.success('curl 解析成功，请配置字段映射')
      templateCurlModalVisible.value = false
      templateCurlConfigModalVisible.value = true
    } else {
      message.error(res.msg || '解析失败')
    }
  } catch (error: any) {
    message.error(error.message || '解析失败')
  } finally {
    templateCurlModalLoading.value = false
  }
}

// 第二步：应用模板字段映射配置
const handleParseTemplateCurlStep2 = async () => {
  if (!templateCurlForm.parsed_schema) {
    message.warning('请先解析 curl 命令')
    return
  }

  templateCurlConfigModalLoading.value = true
  try {
    const res: any = await api.applyTemplateFieldMapping({
      openapi_schema: templateCurlForm.parsed_schema,
      field_mapping: {
        template_name_path: templateCurlForm.template_name_path,
        template_content_path: templateCurlForm.template_content_path,
        group_name_pattern: templateCurlForm.group_name_pattern,
        parse_prompt: templateCurlForm.parse_prompt,
        template_selector: {
          enabled: modalForm.options.enable_template_selector,
          field_name: modalForm.options.template_selector_field_name,
          field_label: modalForm.options.template_selector_field_label,
          label_path: modalForm.options.template_selector_label_path,
          value_path: modalForm.options.template_selector_value_path,
        },
      },
    })
    if (res.code === 200) {
      // 将生成的 Schema 填入表单
      modalForm.options.api_schema = res.data.openapi_schema
      message.success('字段映射配置成功，已生成模板 API Schema')
      templateCurlConfigModalVisible.value = false
    } else {
      message.error(res.msg || '配置失败')
    }
  } catch (error: any) {
    message.error(error.message || '配置失败')
  } finally {
    templateCurlConfigModalLoading.value = false
  }
}

const handleCancelTemplateCurlModal = () => {
  templateCurlModalVisible.value = false
}

const handleCancelTemplateCurlConfigModal = () => {
  templateCurlConfigModalVisible.value = false
}

const handleSave = async () => {
  modalLoading.value = true
  try {
    // 先将 Markdown 解析为选项数据
    parseMarkdownToOptions()

    // 清理空选项（下拉单选/多选类型）
    if (modalForm.field_type === 'select_single' || modalForm.field_type === 'select_multi') {
      modalForm.options.items = modalForm.options.items.filter((item: any) => item.value && item.label)
    }
    // 清理空批注（文本输入类型）
    if (modalForm.field_type === 'text') {
      modalForm.corrections = modalForm.corrections.filter((item: any) => item.text)
    }

    const apiFunc = modalAction.value === 'add' ? api.createFieldSpec : api.updateFieldSpec
    const res: any = await apiFunc({ ...modalForm })
    if (res.code === 200) {
      message.success(modalAction.value === 'add' ? '创建成功' : '更新成功')
      crudTableRef.value?.closeModal()
      fetchData()
    } else {
      message.error(res.msg || '操作失败')
    }
  } catch (error: any) {
    message.error(error.message || '操作失败')
  } finally {
    modalLoading.value = false
  }
}

const handleDelete = async (record: any) => {
  try {
    const res: any = await api.deleteFieldSpec({ id: record.id })
    if (res.code === 200) {
      message.success('删除成功')
      fetchData()
    } else {
      message.error(res.msg || '删除失败')
    }
  } catch (error: any) {
    message.error(error.message || '删除失败')
  }
}

// 批量删除字段
const handleBatchDelete = async () => {
  if (selectedRowKeys.value.length === 0) {
    message.warning('请先选择要删除的字段')
    return
  }

  try {
    const res: any = await api.batchDeleteFieldSpecs({
      ids: selectedRowKeys.value
    })

    if (res.code === 200) {
      message.success(`批量删除成功：${res.data.deleted_count} 个字段`)
      selectedRowKeys.value = []
      fetchData()
    } else {
      message.error(res.msg || '批量删除失败')
    }
  } catch (error: any) {
    message.error(error.message || '批量删除失败')
  }
}

// 级联配置相关方法
const showCascadeConfig = async (record: any) => {
  modalForm.id = record.id
  modalForm.field_name = record.field_name
  await fetchFieldCascadeConfigs(record.id)
  crudTableRef.value?.openEditModal(record)
}

// curl 展平配置变更处理
const onCurlFlattenChange = () => {
  if (curlForm.enable_flatten && !curlForm.flatten_label_path2) {
    curlForm.flatten_label_path2 = '$.data[*].children[*].label'
    curlForm.flatten_label_separator = '-'
    curlForm.flatten_value_path2 = '$.data[*].children[*].value'
    curlForm.flatten_value_separator = '-'
  }
}

// 级联配置 curl 展平配置变更处理
const onCascadeCurlFlattenChange = () => {
  if (cascadeCurlForm.enable_flatten && !cascadeCurlForm.flatten_label_path2) {
    cascadeCurlForm.flatten_label_path2 = '$.data[*].children[*].label'
    cascadeCurlForm.flatten_label_separator = '-'
    cascadeCurlForm.flatten_value_path2 = '$.data[*].children[*].value'
    cascadeCurlForm.flatten_value_separator = '-'
  }
}

const fetchFieldCascadeConfigs = async (fieldId: number) => {
  try {
    const params: any = { parent_field_id: fieldId }
    // 超管传递租户ID
    if (userStore.isSuperUser && modalForm.tenant_id) {
      params.tenant_id = modalForm.tenant_id
    }
    const res: any = await api.getCascadeConfigList(params)
    if (res.code === 200) {
      fieldCascadeConfigs.value = res.data?.configs || []
    }
  } catch (error) {
    console.error('获取级联配置失败', error)
    fieldCascadeConfigs.value = []
  }
}

// 动态参数相关方法
const addDynamicParam = () => {
  if (!cascadeConfig.dynamic_params) {
    cascadeConfig.dynamic_params = []
  }
  cascadeConfig.dynamic_params.push({ key: '', value: '' })
}

const removeDynamicParam = (index: number) => {
  if (cascadeConfig.dynamic_params) {
    cascadeConfig.dynamic_params.splice(index, 1)
  }
}

const showAddCascadeModal = () => {
  if (!modalForm.id) {
    message.warning('请先保存字段后再添加级联配置')
    return
  }
  resetCascadeConfig()
  cascadeConfig.parent_field_id = modalForm.id
  cascadeModalVisible.value = true
}

const editCascadeConfig = (item: any) => {
  cascadeConfig.id = item.id
  cascadeConfig.parent_field_id = item.parent_field_id
  cascadeConfig.field_name_pattern = item.field_name_pattern || 'parent.$.data[*].label + -的二三级'
  cascadeConfig.field_label_pattern = item.field_label_pattern || 'parent.$.data[*].label + -的二三级'
  cascadeConfig.dynamic_params = item.dynamic_params || []
  cascadeConfig.api_schema = item.api_schema || ''

  cascadeModalVisible.value = true
}

const resetCascadeConfig = () => {
  cascadeConfig.id = undefined
  cascadeConfig.parent_field_id = undefined
  cascadeConfig.field_name_pattern = 'parent.$.data[*].label + -的二三级'
  cascadeConfig.field_label_pattern = 'parent.$.data[*].label + -的二三级'
  cascadeConfig.dynamic_params = []
  cascadeConfig.api_schema = ''
}

// 应用动态参数到 api_schema
const applyDynamicParamsToSchema = () => {
  if (!cascadeConfig.api_schema) return cascadeConfig.api_schema

  try {
    const schema = yaml.load(cascadeConfig.api_schema) as any

    // 遍历所有 paths 和 methods，添加 x-api-params
    if (schema.paths) {
      for (const path in schema.paths) {
        for (const method in schema.paths[path]) {
          const operation = schema.paths[path][method]
          if (cascadeConfig.dynamic_params && cascadeConfig.dynamic_params.length > 0) {
            if (!operation['x-api-params']) {
              operation['x-api-params'] = {}
            }
            // 添加动态参数
            cascadeConfig.dynamic_params.forEach(param => {
              if (param.key && param.value) {
                operation['x-api-params'][param.key] = param.value
              }
            })
          }
        }
      }
    }

    return yaml.dump(schema)
  } catch (e) {
    console.error('应用动态参数失败:', e)
    return cascadeConfig.api_schema
  }
}

const handleSaveCascadeConfig = async () => {
  if (!cascadeConfig.api_schema) {
    message.warning('请配置OpenAPI Schema')
    return
  }

  // 应用动态参数到 schema
  const finalSchema = applyDynamicParamsToSchema()

  cascadeModalLoading.value = true
  try {
    const apiFunc = cascadeConfig.id ? api.updateCascadeConfig : api.createCascadeConfig
    const res: any = await apiFunc({
      ...cascadeConfig,
      api_schema: finalSchema,
    })
    if (res.code === 200) {
      message.success('保存成功')
      cascadeModalVisible.value = false
      if (cascadeConfig.parent_field_id) {
        await fetchFieldCascadeConfigs(cascadeConfig.parent_field_id)
      }
    } else {
      message.error(res.msg || '保存失败')
    }
  } catch (error: any) {
    message.error(error.message || '保存失败')
  } finally {
    cascadeModalLoading.value = false
  }
}

const showCascadeCurlModal = () => {
  cascadeCurlForm.curl_command = ''
  cascadeCurlForm.label_path = '$.data[*].label'
  cascadeCurlForm.value_path = '$.data[*].value'
  cascadeCurlForm.enable_flatten = false
  cascadeCurlForm.parsed_schema = ''
  cascadeCurlModalVisible.value = true
}

// 第一步：解析 curl 命令为 YAML
const handleParseCascadeCurlStep1 = async () => {
  if (!cascadeCurlForm.curl_command.trim()) {
    message.warning('请输入 curl 命令')
    return
  }

  cascadeCurlModalLoading.value = true
  try {
    const res: any = await api.parseCurlCommand({
      curl_command: cascadeCurlForm.curl_command,
      // 第一步不传 label_path 和 value_path，只解析 curl 为 YAML
    })
    if (res.code === 200) {
      // 临时存储解析后的 schema
      cascadeCurlForm.parsed_schema = res.data.openapi_schema
      message.success('curl 解析成功，请配置字段映射')
      cascadeCurlModalVisible.value = false
      cascadeCurlConfigModalVisible.value = true
    } else {
      message.error(res.msg || '解析失败')
    }
  } catch (error: any) {
    message.error(error.message || '解析失败')
  } finally {
    cascadeCurlModalLoading.value = false
  }
}

// 第二步：应用 JSONPath 和展平配置
const handleParseCascadeCurlStep2 = async () => {
  if (!cascadeCurlForm.parsed_schema) {
    message.warning('请先解析 curl 命令')
    return
  }

  cascadeCurlConfigModalLoading.value = true
  try {
    const res: any = await api.applyFieldMapping({
      openapi_schema: cascadeCurlForm.parsed_schema,
      label_path: cascadeCurlForm.label_path,
      value_path: cascadeCurlForm.value_path,
      enable_flatten: cascadeCurlForm.enable_flatten,
      flatten_config: cascadeCurlForm.enable_flatten ? {
        label_path_level2: cascadeCurlForm.flatten_label_path2,
        label_path_level3: cascadeCurlForm.flatten_label_path3,
        label_separator: cascadeCurlForm.flatten_label_separator,
        value_path_level2: cascadeCurlForm.flatten_value_path2,
        value_path_level3: cascadeCurlForm.flatten_value_path3,
        value_separator: cascadeCurlForm.flatten_value_separator,
      } : undefined,
    })
    if (res.code === 200) {
      cascadeConfig.api_schema = res.data.openapi_schema
      message.success('字段映射配置成功，已生成 OpenAPI Schema')
      cascadeCurlConfigModalVisible.value = false
    } else {
      message.error(res.msg || '配置失败')
    }
  } catch (error: any) {
    message.error(error.message || '配置失败')
  } finally {
    cascadeCurlConfigModalLoading.value = false
  }
}

const handleCancelCascadeCurlModal = () => {
  cascadeCurlModalVisible.value = false
}

const handleCancelCascadeCurlConfigModal = () => {
  cascadeCurlConfigModalVisible.value = false
}

const handleCancelCascadeModal = () => {
  cascadeModalVisible.value = false
}

const syncCascadeConfig = async (item: any) => {
  item.syncing = true
  try {
    const params: any = { config_id: item.id }
    // 超管传递租户ID
    if (userStore.isSuperUser && modalForm.tenant_id) {
      params.tenant_id = modalForm.tenant_id
    }
    const res: any = await api.syncCascadeFields(params)
    if (res.code === 200) {
      message.success(`同步成功: ${res.data?.synced_count || 0}/${res.data?.total_count || 0}`)
      // 使用当前编辑的字段ID刷新级联配置列表
      if (modalForm.id) {
        await fetchFieldCascadeConfigs(modalForm.id)
      }
    } else {
      message.error(res.msg || '同步失败')
    }
  } catch (error: any) {
    message.error(error.message || '同步失败')
  } finally {
    item.syncing = false
  }
}

const deleteCascadeConfig = async (item: any) => {
  try {
    const params: any = { config_id: item.id }
    // 超管传递租户ID
    if (userStore.isSuperUser && modalForm.tenant_id) {
      params.tenant_id = modalForm.tenant_id
    }
    const res: any = await api.deleteCascadeConfig(params)
    if (res.code === 200) {
      message.success('删除成功')
      if (cascadeConfig.parent_field_id) {
        await fetchFieldCascadeConfigs(cascadeConfig.parent_field_id)
      }
    } else {
      message.error(res.msg || '删除失败')
    }
  } catch (error: any) {
    message.error(error.message || '删除失败')
  }
}

watch(() => props.fieldGroupId, (newVal) => {
  // 字段组ID变更时的处理
  // 使用 nextTick 确保查询参数更新后再获取数据
  nextTick(() => {
    fetchData()
  })
}, { immediate: true })

onMounted(() => {
  fetchTenantOptions()
  fetchAppOptions(queryParams.tenant_id)
  fetchData()
})
</script>

<style scoped lang="less">
.field-spec-management {

  .option-item,
  .correction-item,
  .header-item {
    margin-bottom: 8px;
  }

  .selection-limit-item {
    .limit-input-wrapper {
      display: flex;
      flex-direction: column;

      .limit-label {
        font-size: 14px;
        color: rgba(0, 0, 0, 0.85);
        margin-bottom: 8px;
        line-height: 1.5715;
      }
    }
  }
}
</style>
