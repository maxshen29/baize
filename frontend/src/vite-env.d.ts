/// <reference types="vite/client" />

// 第三方库缺少类型声明时的兜底（运行时由 npm 安装的实体提供）
declare module 'echarts-gl'
declare module 'xlsx' {
  const XLSX: any
  export function read(data: any, opts?: any): any
  export const utils: any
  export default XLSX
}

