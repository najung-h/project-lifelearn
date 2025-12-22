import axios from 'axios';

// Axios 인스턴스 생성
const api = axios.create({
  baseURL: 'http://localhost/api/v1', // 백엔드 API 주소
  headers: {
    'Content-Type': 'application/json',
  },
});

// 쿠키에서 값 가져오는 헬퍼 함수
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      // 이 쿠키 문자열이 이름으로 시작하는지 확인
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

// 요청 인터셉터: 요청 보낼 때 토큰 및 CSRF 토큰 헤더 추가
api.interceptors.request.use(
  (config) => {
    // Auth Token
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers['Authorization'] = `Token ${token}`;
    }
    
    // CSRF Token
    const csrfToken = getCookie('csrftoken');
    if (csrfToken) {
      config.headers['X-CSRFToken'] = csrfToken;
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 응답 인터셉터: (선택) 에러 처리 공통화 등
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // 예: 401 Unauthorized 에러 시 로그아웃 처리 등
    return Promise.reject(error);
  }
);

export default api;
