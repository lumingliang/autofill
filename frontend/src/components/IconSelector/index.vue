<template>
  <div class="icon-selector" @click="openSelector">
    <div class="icon-selector-trigger" :class="{ 'has-icon': selectedIcon }">
      <span class="icon-display">
        <component :is="selectedIconComponent" v-if="selectedIcon" />
        <span v-else class="placeholder-icon">📋</span>
      </span>
      <span class="icon-name-display">{{ selectedIcon || '请选择图标' }}</span>
      <DownOutlined class="arrow-icon" :class="{ 'rotate-180': visible }" />
    </div>

    <a-modal :open="visible" title="选择图标" width="800px" :footer="null" @cancel="visible = false"
      @update:open="visible = $event">
      <div class="icon-selector-content">
        <a-form-item-rest>
          <!-- 搜索栏 -->
          <a-input :value="searchText" placeholder="搜索图标"
            @change="(e: any) => { searchText = e.target.value; handleSearch(); }">
            <template #suffix>
              <SearchOutlined />
            </template>
          </a-input>

          <!-- 分类标签 -->
          <a-tabs v-model:activeKey="activeCategory" @change="handleCategoryChange">
            <a-tab-pane v-for="category in iconCategories" :key="category.key" :tab="category.label" />
          </a-tabs>

          <!-- 图标列表 -->
          <div class="icon-list">
            <div v-for="icon in filteredIcons" :key="icon.name"
              :class="['icon-item', { active: selectedIcon === icon.name }]" @click="selectIcon(icon.name)">
              <component :is="getIcon(icon.name)" />
              <span class="icon-name">{{ icon.name }}</span>
            </div>
          </div>

          <!-- 分页 -->
          <div class="pagination-wrapper">
            <a-pagination v-model:current="currentPage" v-model:pageSize="pageSize" :total="totalIcons"
              :pageSizeOptions="['48', '96', '144']" show-size-changer @change="handlePageChange"
              @showSizeChange="handlePageChange" />
          </div>
        </a-form-item-rest>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import * as Icons from '@ant-design/icons-vue';
import { DownOutlined, SearchOutlined } from '@ant-design/icons-vue';
import { computed, ref, watch } from 'vue';

const props = defineProps<{
  value?: string
}>()

const emit = defineEmits<{
  'update:value': [value: string]
  change: [value: string]
}>()

const visible = ref(false)
const searchText = ref('')
const activeCategory = ref('all')
const currentPage = ref(1)
const pageSize = ref(48)
const selectedIcon = ref(props.value || '')

// 图标分类
const iconCategories = [
  { key: 'all', label: '全部' },
  { key: 'direction', label: '方向' },
  { key: 'suggestion', label: '提示' },
  { key: 'editor', label: '编辑' },
  { key: 'data', label: '数据' },
  { key: 'brand', label: '品牌' },
  { key: 'general', label: '通用' },
]

// 常用图标列表（精选）
const commonIcons = [
  // 方向类
  'UpOutlined', 'DownOutlined', 'LeftOutlined', 'RightOutlined',
  'UpCircleOutlined', 'DownCircleOutlined', 'LeftCircleOutlined', 'RightCircleOutlined',
  'ArrowUpOutlined', 'ArrowDownOutlined', 'ArrowLeftOutlined', 'ArrowRightOutlined',
  'SwapOutlined', 'RollbackOutlined', 'EnterOutlined', 'RetweetOutlined',

  // 提示类
  'QuestionOutlined', 'QuestionCircleOutlined', 'InfoOutlined', 'InfoCircleOutlined',
  'ExclamationOutlined', 'ExclamationCircleOutlined', 'CloseOutlined', 'CloseCircleOutlined',
  'CheckOutlined', 'CheckCircleOutlined', 'WarningOutlined', 'StopOutlined',

  // 编辑类
  'EditOutlined', 'FormOutlined', 'CopyOutlined', 'ScissorOutlined',
  'DeleteOutlined', 'SnippetsOutlined', 'DiffOutlined', 'HighlightOutlined',
  'AlignLeftOutlined', 'AlignCenterOutlined', 'AlignRightOutlined', 'BgColorsOutlined',

  // 数据类
  'AreaChartOutlined', 'PieChartOutlined', 'BarChartOutlined', 'DotChartOutlined',
  'LineChartOutlined', 'RadarChartOutlined', 'HeatMapOutlined', 'FallOutlined',
  'RiseOutlined', 'StockOutlined', 'BoxPlotOutlined', 'FundOutlined',

  // 品牌和标识
  'AndroidOutlined', 'AppleOutlined', 'WindowsOutlined', 'IeOutlined',
  'ChromeOutlined', 'GithubOutlined', 'AliwangwangOutlined', 'WeiboOutlined',
  'WechatOutlined', 'Html5Outlined', 'AlipayOutlined', 'TaobaoOutlined',

  // 通用 - 用户相关
  'UserOutlined', 'TeamOutlined', 'UserAddOutlined', 'UserDeleteOutlined',
  'UserSwitchOutlined', 'ContactsOutlined', 'SolutionOutlined', 'IdcardOutlined',

  // 通用 - 文件相关
  'FileOutlined', 'FileTextOutlined', 'FileAddOutlined', 'FileExcelOutlined',
  'FileWordOutlined', 'FilePdfOutlined', 'FileImageOutlined', 'FileZipOutlined',
  'FolderOutlined', 'FolderOpenOutlined', 'FolderAddOutlined', 'FolderViewOutlined',

  // 通用 - 系统相关
  'HomeOutlined', 'SettingOutlined', 'ToolOutlined', 'SafetyOutlined',
  'SecurityScanOutlined', 'SafetyCertificateOutlined', 'InsuranceOutlined', 'AlertOutlined',

  // 通用 - 导航相关
  'MenuOutlined', 'BarsOutlined', 'AppstoreOutlined', 'AppstoreAddOutlined',
  'UnorderedListOutlined', 'OrderedListOutlined', 'TableOutlined', 'ProfileOutlined',

  // 通用 - 操作相关
  'SearchOutlined', 'ReloadOutlined', 'SyncOutlined', 'UndoOutlined',
  'RedoOutlined', 'LoadingOutlined', 'PoweroffOutlined', 'LogoutOutlined',
  'LoginOutlined', 'ExportOutlined', 'ImportOutlined', 'DownloadOutlined',
  'UploadOutlined', 'CloudUploadOutlined', 'CloudDownloadOutlined', 'CloudOutlined',

  // 通用 - 其他常用
  'StarOutlined', 'HeartOutlined', 'LikeOutlined', 'DislikeOutlined',
  'EyeOutlined', 'EyeInvisibleOutlined', 'LockOutlined', 'UnlockOutlined',
  'MailOutlined', 'PhoneOutlined', 'MessageOutlined', 'NotificationOutlined',
  'BellOutlined', 'CalendarOutlined', 'ClockCircleOutlined', 'HistoryOutlined',
  'PrinterOutlined', 'ShareAltOutlined', 'ShoppingCartOutlined', 'ShoppingOutlined',
  'GiftOutlined', 'TrophyOutlined', 'CrownOutlined', 'FireOutlined',
  'BulbOutlined', 'RocketOutlined', 'ThunderboltOutlined', 'GlobalOutlined',
  'ClusterOutlined', 'DeploymentUnitOutlined', 'ApartmentOutlined', 'ShopOutlined',
  'BankOutlined', 'HospitalOutlined', 'SchoolOutlined', 'HotelOutlined',
  'CarOutlined', 'TruckOutlined', 'EnvironmentOutlined', 'CompassOutlined',
  'DashboardOutlined', 'ControlOutlined', 'ExperimentOutlined', 'ApiOutlined',
  'BugOutlined', 'CodeOutlined', 'BranchesOutlined', 'ForkOutlined',
  'RobotOutlined', 'CloudServerOutlined', 'DatabaseOutlined', 'ServerOutlined',
  'DesktopOutlined', 'LaptopOutlined', 'MobileOutlined', 'TabletOutlined',
  'WifiOutlined', 'LinkOutlined', 'PaperClipOutlined', 'TagOutlined',
  'TagsOutlined', 'FlagOutlined', 'PushpinOutlined', 'BookOutlined',
  'ReadOutlined', 'ContainerOutlined', 'WalletOutlined', 'CreditCardOutlined',
  'TransactionOutlined', 'DollarOutlined', 'EuroOutlined', 'PoundOutlined',
  'PercentageOutlined', 'CalculatorOutlined', 'ReconciliationOutlined', 'AuditOutlined',
  'FileSearchOutlined', 'FileProtectOutlined', 'FileSyncOutlined', 'FileDoneOutlined',
  'ScheduleOutlined', 'CarryOutOutlined', 'ProjectOutlined', 'FundProjectionScreenOutlined',
  'SlidersOutlined', 'SwitcherOutlined', 'FilterOutlined', 'SortAscendingOutlined',
  'SortDescendingOutlined', 'ColumnHeightOutlined', 'ColumnWidthOutlined', 'DragOutlined',
  'MoreOutlined', 'EllipsisOutlined', 'PlusOutlined', 'MinusOutlined',
  'PlusCircleOutlined', 'MinusCircleOutlined', 'PlusSquareOutlined', 'MinusSquareOutlined',
  'CheckSquareOutlined', 'BorderOutlined', 'BorderlessTableOutlined', 'InsertRowAboveOutlined',
  'InsertRowBelowOutlined', 'InsertRowLeftOutlined', 'InsertRowRightOutlined',
  'MergeCellsOutlined', 'SplitCellsOutlined', 'SubnodeOutlined', 'SisternodeOutlined',
  'PartitionOutlined', 'GroupOutlined', 'UngroupOutlined', 'TranslationOutlined',
  'FormatPainterOutlined', 'ClearOutlined', 'ExpandOutlined', 'CompressOutlined',
  'FullscreenOutlined', 'FullscreenExitOutlined', 'ZoomInOutlined', 'ZoomOutOutlined',
]

// 分类映射
const categoryMap: Record<string, string[]> = {
  direction: ['Up', 'Down', 'Left', 'Right', 'Arrow', 'Swap', 'Rollback', 'Enter', 'Retweet'],
  suggestion: ['Question', 'Info', 'Exclamation', 'Close', 'Check', 'Warning', 'Stop'],
  editor: ['Edit', 'Form', 'Copy', 'Scissor', 'Delete', 'Snippets', 'Diff', 'Highlight', 'Align', 'BgColors'],
  data: ['Chart', 'Plot', 'Fall', 'Rise', 'Stock', 'Fund', 'HeatMap'],
  brand: ['Android', 'Apple', 'Windows', 'Ie', 'Chrome', 'Github', 'Aliwangwang', 'Weibo', 'Wechat', 'Html5', 'Alipay', 'Taobao'],
  general: [], // 其他都归为通用
}

// 获取图标组件
const iconList = computed(() => {
  return commonIcons
    .filter(name => Icons[name as keyof typeof Icons])
    .map(name => ({
      name,
      component: Icons[name as keyof typeof Icons],
      category: getCategory(name),
    }))
})

// 获取图标分类
function getCategory(name: string): string {
  for (const [cat, keywords] of Object.entries(categoryMap)) {
    if (keywords.some(kw => name.includes(kw))) {
      return cat
    }
  }
  return 'general'
}

// 过滤后的图标
const filteredIcons = computed(() => {
  let result = iconList.value

  // 按分类过滤
  if (activeCategory.value !== 'all') {
    result = result.filter(icon => icon.category === activeCategory.value)
  }

  // 按搜索文本过滤
  if (searchText.value) {
    const search = searchText.value.toLowerCase()
    result = result.filter(icon => icon.name.toLowerCase().includes(search))
  }

  // 分页
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return result.slice(start, end)
})

const totalIcons = computed(() => {
  let result = iconList.value
  if (activeCategory.value !== 'all') {
    result = result.filter(icon => icon.category === activeCategory.value)
  }
  if (searchText.value) {
    const search = searchText.value.toLowerCase()
    result = result.filter(icon => icon.name.toLowerCase().includes(search))
  }
  return result.length
})

// 获取图标组件
function getIcon(name?: string): any {
  if (!name) return null
  return Icons[name as keyof typeof Icons] || null
}

// 当前选中图标组件
const selectedIconComponent = computed<any>(() => {
  if (!selectedIcon.value) return null
  return Icons[selectedIcon.value as keyof typeof Icons] || null
})

// 打开选择器
function openSelector() {
  visible.value = true
  searchText.value = ''
  activeCategory.value = 'all'
  currentPage.value = 1
}

// 选择图标
function selectIcon(name: string) {
  selectedIcon.value = name
  emit('update:value', name)
  emit('change', name)
  visible.value = false
}

// 搜索
function handleSearch() {
  currentPage.value = 1
}

// 切换分类
function handleCategoryChange() {
  currentPage.value = 1
}

// 分页变化
function handlePageChange() {
  // 分页变化时保持当前位置
}

// 监听props变化
watch(() => props.value, (newVal) => {
  selectedIcon.value = newVal || ''
})
</script>

<style scoped lang="less">
.icon-selector {
  width: 100%;
  cursor: pointer;

  .icon-selector-trigger {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 11px;
    border: 1px solid #d9d9d9;
    border-radius: 4px;
    background-color: #fff;
    transition: all 0.3s;
    min-height: 32px;

    &:hover {
      border-color: #40a9ff;
    }

    &.has-icon {
      border-color: #40a9ff;
    }

    .icon-display {
      display: flex;
      align-items: center;
      font-size: 16px;
      color: #666;
    }

    .placeholder-icon {
      font-size: 14px;
      opacity: 0.5;
    }

    .icon-name-display {
      flex: 1;
      color: #333;
      font-size: 14px;

      &:empty::before {
        content: '请选择图标';
        color: #bfbfbf;
      }
    }

    .arrow-icon {
      font-size: 12px;
      color: #999;
      transition: transform 0.3s;

      &.rotate-180 {
        transform: rotate(180deg);
      }
    }
  }
}

.icon-selector-content {
  padding: 16px 0;

  :deep(.ant-tabs) {
    margin-top: 16px;
  }

  .icon-list {
    display: grid;
    grid-template-columns: repeat(8, 1fr);
    gap: 8px;
    max-height: 400px;
    overflow-y: auto;
    padding: 16px 0;

    .icon-item {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 12px 8px;
      border: 1px solid #f0f0f0;
      border-radius: 4px;
      cursor: pointer;
      transition: all 0.3s;

      &:hover {
        border-color: #1890ff;
        color: #1890ff;
        background-color: #e6f7ff;
      }

      &.active {
        border-color: #1890ff;
        background-color: #1890ff;
        color: #fff;

        .icon-name {
          color: #fff;
        }
      }

      :deep(.anticon) {
        font-size: 24px;
        margin-bottom: 4px;
      }

      .icon-name {
        font-size: 12px;
        color: #666;
        text-align: center;
        word-break: break-all;
        line-height: 1.2;
        max-width: 100%;
      }
    }
  }

  .pagination-wrapper {
    display: flex;
    justify-content: flex-end;
    padding-top: 16px;
    border-top: 1px solid #f0f0f0;
  }
}

@media (max-width: 768px) {
  .icon-selector-content {
    .icon-list {
      grid-template-columns: repeat(4, 1fr);
    }
  }
}
</style>
