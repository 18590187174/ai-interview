<template>
  <div class="home">
    <section class="hero">
      <span class="hero-badge">
        <span class="pulse-dot" aria-hidden="true"></span>
        AI 驱动 · 面试准备助手
      </span>
      <h1 class="hero-title">
        让每一次面试前，<span class="gradient-text">都有备而来</span>
      </h1>
      <p class="hero-subtitle">
        围绕「简历押题 → 开始面试 → 面试报告」一条主线，帮你更高效地准备真实面试。
      </p>
    </section>

    <section class="steps">
      <router-link
        v-for="step in steps"
        :key="step.title"
        :to="step.to"
        class="step-card"
      >
        <div class="card-glow" aria-hidden="true"></div>
        <div class="step-head">
          <span class="step-icon" aria-hidden="true" v-html="step.icon"></span>
          <span class="step-index">{{ step.index }}</span>
        </div>
        <h3>{{ step.title }}</h3>
        <p>{{ step.description }}</p>
        <span class="card-cta">
          {{ step.cta }}
          <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M5 12h14M13 6l6 6-6 6" />
          </svg>
        </span>
      </router-link>
    </section>
  </div>
</template>

<script setup lang="ts">
const steps = [
  {
    index: '01',
    title: '简历押题',
    description: '填写目标岗位、工作年限、岗位描述与编程语言，上传简历后结合知识库生成最可能被问到的题目。',
    cta: '开始押题',
    to: '/resume-quiz',
    icon: '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/><path d="M9 13h6M9 17h4"/></svg>',
  },
  {
    index: '02',
    title: '开始面试',
    description: '一问一答模拟真实面试场景，支持打字与语音两种方式作答。',
    cta: '进入面试',
    to: '/interview',
    icon: '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a8 8 0 0 1-8 8H5l-2 2V12a8 8 0 0 1 8-8h2a8 8 0 0 1 8 8z"/><path d="M9 11h.01M13 11h.01M17 11h.01"/></svg>',
  },
  {
    index: '03',
    title: '面试报告',
    description: '面试结束后给出评分、参考答案与针对你实际回答的改进建议，可在「我的」中回看。',
    cta: '查看我的',
    to: '/profile',
    icon: '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="M8 17V9M13 17V5M18 17v-7"/></svg>',
  },
]
</script>

<style scoped>
.home {
  max-width: 1080px;
  margin: 0 auto;
}

.hero {
  padding: 40px 0 12px;
  text-align: center;
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  border-radius: 999px;
  border: 1px solid var(--surface-border);
  background: var(--surface-glass);
  color: var(--text-secondary);
  font-size: 12px;
  letter-spacing: 1px;
}

.pulse-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--brand-cyan);
  box-shadow: 0 0 8px var(--glow-cyan);
  animation: pulse 2.4s ease-in-out infinite;
}

@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.35;
  }
}

.hero-title {
  margin: 18px 0 10px;
  font-size: 38px;
  font-weight: 800;
  letter-spacing: 1px;
  color: var(--text-primary);
}

.gradient-text {
  background: var(--brand-gradient);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.hero-subtitle {
  margin: 0;
  font-size: 15px;
  line-height: 1.7;
  color: var(--text-secondary);
}

.steps {
  margin-top: 36px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 20px;
}

.step-card {
  position: relative;
  display: flex;
  flex-direction: column;
  padding: 24px;
  border-radius: var(--radius-card);
  border: 1px solid var(--surface-border);
  background: var(--surface-glass);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  overflow: hidden;
  cursor: pointer;
  transition:
    transform var(--transition-ui),
    border-color var(--transition-ui),
    box-shadow var(--transition-ui);
}

.card-glow {
  position: absolute;
  inset: -40% -20% auto;
  height: 120px;
  background: var(--brand-gradient-soft);
  filter: blur(30px);
  opacity: 0;
  transition: opacity var(--transition-ui);
  pointer-events: none;
}

.step-card:hover {
  transform: translateY(-4px);
  border-color: var(--surface-border-hover);
  box-shadow: var(--shadow-card-hover);
}

.step-card:hover .card-glow {
  opacity: 1;
}

.step-card:focus-visible {
  outline: 2px solid var(--brand-cyan);
  outline-offset: 2px;
}

.step-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.step-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: 12px;
  color: var(--brand-cyan);
  background: rgba(34, 211, 238, 0.1);
  border: 1px solid rgba(34, 211, 238, 0.25);
}

.step-index {
  font-size: 26px;
  font-weight: 800;
  letter-spacing: 2px;
  color: rgba(100, 116, 139, 0.32);
  font-family: 'Segoe UI', sans-serif;
}

.step-card h3 {
  margin: 0 0 8px;
  font-size: 17px;
  color: var(--text-primary);
}

.step-card p {
  margin: 0;
  flex: 1;
  color: var(--text-secondary);
  line-height: 1.7;
  font-size: 13.5px;
}

.card-cta {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: 18px;
  font-size: 13px;
  font-weight: 600;
  color: var(--brand-cyan);
}

.card-cta svg {
  transition: transform var(--transition-ui);
}

.step-card:hover .card-cta svg {
  transform: translateX(4px);
}

@media (prefers-reduced-motion: reduce) {
  .pulse-dot {
    animation: none;
  }
}
</style>
