/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // v11.0 净白浅蓝 SaaS 视觉规范
        brand: {
          primary: '#3B82F6',        // 主色（浅蓝）
          'primary-light': '#60A5FA',
          active: '#2563EB',
          'bg-warm': '#F8FAFC',      // 页面底色（净白浅蓝）
          ink: '#0F172A',           // 主文字
          line: '#E2E8F0',          // 描边/分隔
          muted: '#64748B',         // 次级文字
          surface: '#FFFFFF',       // 卡片底色
          soft: '#F1F5F9',          // 浅填充（chip/分组）
          'soft-blue': '#EFF6FF',   // 蓝色浅底
          success: '#10B981',
          warning: '#F59E0B',
          danger: '#EF4444',
        }
      },
      fontFamily: {
        sans: ['Noto Sans SC', 'system-ui', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
