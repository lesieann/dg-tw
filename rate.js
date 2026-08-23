/* 匯率讀取 — index.html 與 quote.html 共用
 *
 * 設計重點：
 *  1. 同源的 rate.json 最快也最可靠，優先使用；失敗才退到 CDN 鏡像。
 *  2. 破快取參數每 5 分鐘才變一次。每次都變會讓瀏覽器與 CDN 快取全部失效，
 *     每位訪客每次開頁都直打來源——anvia.yuan 就是這樣被 GitHub 限流（429）的。
 *  3. 每個請求都有逾時。沒有逾時的話，請求「卡住不回應」會讓畫面永遠停在載入中，
 *     既不顯示匯率也不顯示失敗。
 */

const RATE_SOURCES = [
  'https://cdn.jsdelivr.net/gh/lesieann/dg-tw@main/rate.json',
  'https://cdn.statically.io/gh/lesieann/dg-tw/main/rate.json',
];
const RATE_TIMEOUT_MS = 8000;
const RATE_CACHE_BUCKET_MS = 300000;

async function fetchJsonWithTimeout(url, ms) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), ms);
  try {
    const res = await fetch(url, { signal: ctrl.signal });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();
    if (!(data && data.rate)) throw new Error('unexpected payload');
    return data;
  } finally {
    clearTimeout(timer);
  }
}

/** 取得 { rate, time, source, rate_date }，全部來源皆失敗時丟出例外 */
async function loadRate() {
  const bucket = Math.floor(Date.now() / RATE_CACHE_BUCKET_MS);

  // 同源檔案就在旁邊，先試它
  try {
    return await fetchJsonWithTimeout(`rate.json?t=${bucket}`, RATE_TIMEOUT_MS);
  } catch (e) {
    // 同源不可用時才動用外部鏡像，並且同時發送、取最快回應的
    return await Promise.any(
      RATE_SOURCES.map(url => fetchJsonWithTimeout(`${url}?t=${bucket}`, RATE_TIMEOUT_MS))
    );
  }
}
