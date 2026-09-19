<script setup>
import { onMounted, ref } from 'vue'
import { deleteJSON, getJSON, postJSON } from '../api'
import { fmtTime } from '../utils/time'
import TierLadder from '../components/TierLadder.vue'
import SegmentTable from '../components/SegmentTable.vue'

const accounts = ref([])
const accountId = ref(null)
const kwh = ref(null)
const peak = ref(false)
const result = ref(null)
const summary = ref(null)
const errorMsg = ref('')

const resetForm = () => {
  kwh.value = null
  peak.value = false
  result.value = null
  errorMsg.value = ''
}

const loadSummary = async () => {
  summary.value = null
  resetForm()
  if (!accountId.value) return
  try {
    const s = await getJSON(`/api/accounts/${accountId.value}/last-calc`)
    summary.value = s
    kwh.value = s.kwh
    peak.value = s.peak
  } catch (e) {
    // 404: 该户尚无成功测算，保持空白表单
  }
}

const run = async () => {
  errorMsg.value = ''
  result.value = null
  const submittedKwh = kwh.value
  const submittedPeak = peak.value
  try {
    result.value = await postJSON('/api/bill', {
      account_id: accountId.value,
      kwh: submittedKwh,
      peak: submittedPeak,
      persist: true,
    })
    if (accountId.value) {
      // 刷新摘要（成功时间/运行 id）；表单值即本次提交值，保持不动
      summary.value = await getJSON(`/api/accounts/${accountId.value}/last-calc`)
    }
  } catch (e) {
    errorMsg.value = '测算失败或输入被拒绝，上次成功摘要未受影响'
  }
}

const clearSummary = async () => {
  if (!accountId.value) return
  await deleteJSON(`/api/accounts/${accountId.value}/last-calc`)
  summary.value = null
  resetForm()
}

onMounted(async () => {
  accounts.value = (await getJSON('/api/accounts')).items
})
</script>
<template>
  <div class="page work">
    <h1>测算工作台</h1>
    <div class="panel form-row">
      <label>户号
        <select v-model="accountId" @change="loadSummary">
          <option :value="null">不绑定户号</option>
          <option v-for="a in accounts" :key="a.id" :value="a.id">{{ a.name }}（{{ a.meter_no }}）</option>
        </select>
      </label>
      <label>电量(kWh) <input type="number" v-model.number="kwh" min="0" step="1" /></label>
      <label><input type="checkbox" v-model="peak" /> 尖峰系数</label>
      <button @click="run" :disabled="kwh === null || kwh === ''">计算并入库</button>
    </div>

    <div v-if="accountId" class="panel summary">
      <template v-if="summary">
        <p>
          上次成功时间：{{ fmtTime(summary.success_at) }}
          <span class="muted">运行 #{{ summary.run_id }}</span>
        </p>
        <p class="muted">上次合计 ¥{{ summary.total }}（电量 {{ summary.kwh }} kWh · 尖峰 {{ summary.peak ? '开' : '关' }}），已按此回填表单</p>
        <button class="ghost" @click="clearSummary">清除上次摘要</button>
      </template>
      <p v-else class="muted">该户暂无成功测算记录</p>
    </div>

    <p v-if="errorMsg" class="err">{{ errorMsg }}</p>

    <div v-if="result" class="panel">
      <p>合计 ¥{{ result.total }} <span class="muted">记录#{{ result.run_id }}</span></p>
      <TierLadder :segments="result.segments" />
      <SegmentTable :rows="result.segments" />
    </div>
  </div>
</template>
<style scoped>
.form-row { display: flex; flex-wrap: wrap; gap: 1rem; align-items: end; }
input[type=number] { width: 6rem; margin-left: 0.35rem; }
select { margin-left: 0.35rem; }
.summary button.ghost { background: transparent; color: var(--accent); border: 1px solid var(--accent); }
.err { color: #ff8a8a; }
</style>
