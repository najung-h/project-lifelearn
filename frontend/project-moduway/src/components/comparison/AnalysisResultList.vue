<template>
  <div class="result-list-container">

    <!-- Case 1: 분석 중 (로딩 상태) -->
    <div v-if="isLoading" class="loading-container">
      <div class="loading-spinner"></div>
      <h2>AI 분석 진행 중...</h2>
      <p>강좌 정보를 수집하고 맞춤 분석을 진행하고 있습니다. 잠시만 기다려주세요.</p>
    </div>

    <!-- Case 2: 분석 완료 후 (결과 표시) -->
    <template v-else-if="isAnalyzed">
      <!-- AI Comment Boxes (각 강좌별 개인화 코멘트) -->
      <div v-if="personalizedComments && personalizedComments.length > 0" class="comments-section">
        <div
          v-for="(comment, index) in personalizedComments"
          :key="index"
          class="ai-comment-box"
        >
          <div class="comment-content">
            <div class="comment-header">
              <span class="pulse-dot"></span>
              <span class="comment-label">AI 맞춤 코멘트 #{{ index + 1 }}</span>
              <span class="course-badge">{{ comment.course_name }}</span>
            </div>
            <p class="comment-text">"{{ comment.recommendation_reason }}"</p>

            <!-- 핵심 포인트 -->
            <div v-if="comment.key_points && comment.key_points.length > 0" class="key-points">
              <div class="points-title">📌 핵심 포인트</div>
              <ul>
                <li v-for="(point, pIndex) in comment.key_points" :key="pIndex">{{ point }}</li>
              </ul>
            </div>
          </div>
        </div>

        <p class="comment-note">※ AI 분석은 참고용이며 최종 결정은 학습자의 판단이 필요합니다.</p>
      </div>

      <!-- Cards Grid -->
      <div class="cards-grid">
        <AnalysisResultCard
          v-for="res in results"
          :key="res.id"
          :result="res"
        />
      </div>
    </template>

    <!-- Case 3: 분석 전 (사용 가이드) -->
    <div v-else class="guide-container">
      <div class="guide-header">
        <h2>AI 강좌 분석 사용 가이드</h2>
        <p>복잡한 강좌 선택, AI가 나에게 딱 맞는 최적의 강좌를 추천해 드립니다.</p>
      </div>

      <div class="steps-grid">
        <div class="step-item">
          <div class="step-num">1</div>
          <div class="step-content">
            <h3>관심강좌 등록</h3>
            <p>비교하고 싶은 강의를 먼저 <strong>관심강좌</strong>(위시리스트)로 등록해 주세요.</p>
          </div>
        </div>

        <div class="step-item">
          <div class="step-num">2</div>
          <div class="step-content">
            <h3>학습 목표 설정</h3>
            <p>좌측 패널에 <strong>주당 학습 가능 시간</strong>과 구체적인 <strong>학습 목표</strong>를 입력하세요.</p>
          </div>
        </div>

        <div class="step-item">
          <div class="step-num">3</div>
          <div class="step-content">
            <h3>중요도 조절</h3>
            <p>나에게 중요한 기준(실무, 이론 등)의 가중치를 <strong>0~5점</strong>으로 조절해주세요.</p>
          </div>
        </div>

        <div class="step-item">
          <div class="step-num">4</div>
          <div class="step-content">
            <h3>비교 대상 선택</h3>
            <p>관심강좌에 등록돼 있는 강좌들 중에서 비교할 <strong>1~3개를 체크</strong>하세요.</p>
          </div>
        </div>

        <div class="step-item highlight">
          <div class="step-num">5</div>
          <div class="step-content">
            <h3>분석 시작</h3>
            <p>모든 설정이 완료되었다면 좌측 하단의 <strong>[AI 강좌 비교 분석 시작]</strong> 버튼을 클릭하세요!</p>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import AnalysisResultCard from './AnalysisResultCard.vue';

defineProps({
  results: {
    type: Array,
    required: true
  },
  personalizedComments: {
    type: Array,
    default: () => []
  },
  isAnalyzed: {
    type: Boolean,
    default: false
  },
  isLoading: {
    type: Boolean,
    default: false
  }
});
</script>

<style scoped>
.result-list-container {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

/* Loading State */
.loading-container {
  background: white;
  border: 1px solid var(--border);
  border-radius: 24px;
  padding: 60px 40px;
  text-align: center;
}

.loading-spinner {
  width: 50px;
  height: 50px;
  border: 4px solid #f3f4f6;
  border-top: 4px solid var(--primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 24px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.loading-container h2 {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-main);
  margin-bottom: 12px;
}

.loading-container p {
  font-size: 14px;
  color: var(--text-sub);
}

/* Comments Section */
.comments-section {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* AI Comment Box */
.ai-comment-box {
  background: linear-gradient(135deg, #fff0f2 0%, #fff 100%);
  border: 1px solid #ffdce0;
  border-radius: 16px;
  padding: 28px;
  position: relative;
  overflow: hidden;
}

.comment-content {
  position: relative;
  z-index: 1;
}

.comment-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.pulse-dot {
  width: 8px; height: 8px;
  background: var(--primary);
  border-radius: 50%;
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0% { transform: scale(0.95); opacity: 0.7; }
  50% { transform: scale(1.1); opacity: 1; }
  100% { transform: scale(0.95); opacity: 0.7; }
}

.comment-label {
  font-size: 11px;
  font-weight: 800;
  color: var(--primary);
  text-transform: uppercase;
  letter-spacing: 1px;
}

.course-badge {
  background: var(--primary);
  color: white;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 700;
}

.comment-text {
  font-size: 16px;
  font-weight: 600;
  color: #111;
  line-height: 1.7;
  margin-bottom: 16px;
}

.key-points {
  background: white;
  border: 1px solid #ffdce0;
  border-radius: 12px;
  padding: 16px;
  margin-top: 12px;
}

.points-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--primary-dark);
  margin-bottom: 8px;
}

.key-points ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.key-points li {
  font-size: 13px;
  color: #555;
  line-height: 1.6;
  margin-bottom: 6px;
  padding-left: 18px;
  position: relative;
}

.key-points li::before {
  content: "✓";
  position: absolute;
  left: 0;
  color: var(--primary);
  font-weight: 700;
}

.comment-note {
  font-size: 11px;
  color: #888;
  text-align: center;
  padding: 12px;
  background: #f9f9f9;
  border-radius: 8px;
}

/* Cards Grid */
.cards-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 32px;
}

@media (min-width: 1280px) {
  .cards-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

/* Guide Container (New) */
.guide-container {
  background: white;
  border: 1px solid var(--border);
  border-radius: 24px;
  padding: 40px;
  text-align: center;
  box-shadow: 0 4px 20px rgba(0,0,0,0.03);
}

.guide-header h2 {
  font-size: 24px;
  font-weight: 800;
  color: var(--text-main);
  margin-bottom: 10px;
}

.guide-header p {
  color: var(--text-sub);
  font-size: 16px;
  margin-bottom: 40px;
}

.steps-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 15px;
  text-align: left;
}

.step-item {
  display: flex;
  align-items: flex-start;
  gap: 15px;
  padding: 20px;
  background: #f9f9f9;
  border-radius: 12px;
  transition: 0.2s;
}

.step-item:hover {
  background: white;
  box-shadow: 0 4px 12px rgba(0,0,0,0.05);
  transform: translateY(-2px);
}

.step-item.highlight {
  background: #fff0f2;
  border: 1px solid #ffdce0;
}

.step-num {
  width: 28px; height: 28px;
  background: var(--text-main);
  color: white;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-weight: 800;
  font-size: 14px;
  flex-shrink: 0;
  margin-top: 2px;
}

.step-item.highlight .step-num {
  background: var(--primary);
}

.step-content h3 {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-main);
  margin-bottom: 6px;
}

.step-content p {
  font-size: 13px;
  color: var(--text-sub);
  line-height: 1.5;
  margin: 0;
}

.step-content strong {
  color: var(--primary-dark);
}
</style>
