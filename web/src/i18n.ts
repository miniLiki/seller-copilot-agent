export const zh = {
  pages: {
    catalog: "商品目录",
    overview: "库存总览",
    warehouses: "仓库",
    movements: "库存流水",
    purchasing: "采购",
    transfers: "调拨",
    counts: "盘点",
    adjustments: "库存调整",
    sync: "同步"
  },
  fields: {
    search: "搜索",
    skuCode: "SKU 编码",
    title: "标题",
    price: "价格",
    qty: "数量"
  },
  headers: {
    sku: "SKU",
    title: "标题",
    market: "市场",
    price: "价格",
    status: "状态",
    warehouse: "仓库",
    onHand: "现有库存",
    allocated: "已分配",
    available: "可售库存",
    inbound: "在途库存",
    damaged: "破损",
    quarantine: "隔离",
    risk: "风险",
    code: "编码",
    name: "名称",
    type: "类型",
    qty: "数量",
    onHandDelta: "现有库存变化",
    allocatedDelta: "分配库存变化",
    reason: "原因",
    created: "创建时间",
    po: "采购单",
    lines: "明细数",
    transfer: "调拨单",
    area: "区域",
    currentSupport: "当前支持",
    approval: "审批",
    job: "任务",
    summary: "摘要"
  },
  buttons: {
    createSku: "创建 SKU",
    createPo: "创建采购单",
    createTransfer: "创建调拨单",
    runSync: "执行同步",
    refresh: "刷新"
  }
};

export function displayStatus(value: string) {
  const map: Record<string, string> = {
    active: "启用",
    inactive: "停用",
    pending: "待处理",
    completed: "已完成",
    created: "已创建",
    approved: "已批准",
    rejected: "已拒绝",
    failed: "失败"
  };
  return map[value] ?? value;
}

export function displayMovementType(value: string) {
  const map: Record<string, string> = {
    receive: "入库",
    allocate: "分配",
    release: "释放",
    ship: "发货",
    damage: "报损",
    return: "退货"
  };
  return map[value] ?? value;
}

export function displayRisk(value: string) {
  const map: Record<string, string> = {
    low: "低",
    medium: "中",
    high: "高"
  };
  return map[value] ?? value;
}
