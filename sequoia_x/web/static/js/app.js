/* Sequoia-X Web Dashboard 共享 JS 工具 */

/**
 * 封装 fetch，自动处理 JSON 和错误
 */
async function api(url, options = {}) {
    const resp = await fetch(url, {
        headers: { 'Content-Type': 'application/json' },
        ...options,
    });
    if (!resp.ok) {
        const text = await resp.text();
        throw new Error(`${resp.status}: ${text}`);
    }
    return resp.json();
}

/**
 * 显示 toast 通知
 */
function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    const id = 'toast-' + Date.now();
    const bgClass = type === 'success' ? 'bg-success' : type === 'error' ? 'bg-danger' : 'bg-info';
    const html = `
        <div id="${id}" class="toast align-items-center text-white ${bgClass} border-0" role="alert">
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `;
    container.insertAdjacentHTML('beforeend', html);
    const el = document.getElementById(id);
    const toast = new bootstrap.Toast(el, { delay: 3000 });
    toast.show();
    el.addEventListener('hidden.bs.toast', () => el.remove());
}

/**
 * 轮询任务状态直到完成
 */
async function pollTask(taskId, onProgress) {
    while (true) {
        const data = await api(`/api/tasks/${taskId}`);
        if (onProgress) onProgress(data);
        if (data.status === 'done' || data.status === 'error') {
            return data;
        }
        await new Promise(r => setTimeout(r, 1500));
    }
}

/**
 * 雪球代码格式化
 */
function toXueqiuCode(code) {
    if (code.startsWith('6')) return 'SH' + code;
    if (code.startsWith('4') || code.startsWith('8')) return 'BJ' + code;
    return 'SZ' + code;
}

/**
 * 雪球链接生成
 */
function xueqiuLink(code) {
    return `https://xueqiu.com/S/${toXueqiuCode(code)}`;
}
