/**
 * 家庭门户 — 前端公共逻辑
 * 东华倪家
 */

const API_BASE = '/api';

// ========== 当前用户管理 ==========
let currentUser = JSON.parse(localStorage.getItem('family_current_user')) || null;
let members = [];

function getCurrentUserId() {
    return currentUser ? currentUser.id : null;
}

function setCurrentUser(member) {
    currentUser = member;
    localStorage.setItem('family_current_user', JSON.stringify(member));
    updateUserUI();
}

function updateUserUI() {
    const badges = document.querySelectorAll('.current-user-badge');
    badges.forEach(badge => {
        if (currentUser) {
            badge.style.background = currentUser.color;
            badge.innerHTML = `👤 ${currentUser.name}`;
            badge.style.display = 'flex';
        } else {
            badge.style.background = '#94A3B8';
            badge.innerHTML = '👤 选择身份';
            badge.style.display = 'flex';
        }
    });
}

// ========== Toast 消息 ==========
function showToast(message, type = 'info') {
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        toast.style.transition = 'all 0.3s';
        setTimeout(() => toast.remove(), 300);
    }, 2500);
}

// ========== API 封装 ==========
async function api(url, options = {}) {
    const headers = { 'Content-Type': 'application/json' };
    if (options.headers) {
        Object.assign(headers, options.headers);
        delete options.headers;
    }
    // 排除 body 为 FormData 时不设置 Content-Type（让浏览器自动设置）
    if (options.body instanceof FormData) {
        delete headers['Content-Type'];
    }
    const res = await fetch(API_BASE + url, { headers, ...options });
    const data = await res.json();
    if (!res.ok) {
        throw new Error(data.error || '请求失败');
    }
    return data;
}

// ========== 成员加载 ==========
async function loadMembers() {
    try {
        members = await api('/members');
        return members;
    } catch {
        members = [];
        return [];
    }
}

// ========== 身份优先选择遮罩 ==========
async function showIdentityGate() {
    // 如果已有身份，跳过门并触发数据加载
    if (currentUser) {
        const gate = document.getElementById('identity-gate');
        if (gate) gate.classList.add('hidden');
        const main = document.getElementById('main-content');
        if (main) main.style.display = '';
        onUserChanged();
        return;
    }

    // 确保成员已加载
    if (members.length === 0) {
        await loadMembers();
    }

    // 如果加载后还是没有成员（数据库空），也要显示门
    // 如果只有一个成员，自动选择并跳过门
    // 不做自动选择，让用户手动点

    const gate = document.getElementById('identity-gate');
    if (!gate) return;

    renderGateContent();

    // 如果有多个成员，显示门；如果只有0-1个，也显示（让用户添加）
    gate.classList.remove('hidden');
    const main = document.getElementById('main-content');
    if (main) main.style.display = 'none';
}

function renderGateContent() {
    const gate = document.getElementById('identity-gate');
    if (!gate) return;

    gate.innerHTML = `
        <div class="gate-inner">
            <div class="gate-title">🏠 东华倪家</div>
            <div class="gate-subtitle">请选择你的身份</div>
            <div class="gate-member-list" id="gate-member-list">
                ${members.map(m => `
                    <button class="gate-member-card" data-id="${m.id}">
                        <div class="gate-avatar" style="background:${m.color}">${m.name[0]}</div>
                        ${m.name}
                    </button>
                `).join('')}
            </div>
            <button class="gate-add-btn" id="gate-add-btn">＋ 添加新成员</button>
            <div class="gate-add-form" id="gate-add-form">
                <div class="form-row">
                    <input type="text" id="gate-new-name" placeholder="输入成员名称，如：爷爷" maxlength="20">
                    <button id="gate-confirm-add">添加</button>
                </div>
            </div>
        </div>
    `;

    // 点击成员卡片 → 选择身份
    gate.querySelectorAll('.gate-member-card').forEach(card => {
        card.addEventListener('click', () => {
            const id = parseInt(card.dataset.id);
            const member = members.find(m => m.id === id);
            if (member) {
                setCurrentUser(member);
                gate.classList.add('hidden');
                const main = document.getElementById('main-content');
                if (main) main.style.display = '';
                renderUserDropdown();
                onUserChanged();
            }
        });
    });

    // 添加按钮 → 展开输入框
    document.getElementById('gate-add-btn').addEventListener('click', () => {
        document.getElementById('gate-add-form').classList.add('show');
        document.getElementById('gate-add-btn').style.display = 'none';
        setTimeout(() => {
            const input = document.getElementById('gate-new-name');
            if (input) input.focus();
        }, 100);
    });

    // 确认添加
    document.getElementById('gate-confirm-add').addEventListener('click', async () => {
        const input = document.getElementById('gate-new-name');
        const name = input.value.trim();
        if (!name) {
            showToast('请输入成员名称', 'error');
            return;
        }
        try {
            const newMember = await api('/members', {
                method: 'POST',
                body: JSON.stringify({ name })
            });
            members.push(newMember);
            setCurrentUser(newMember);
            gate.classList.add('hidden');
            const main = document.getElementById('main-content');
            if (main) main.style.display = '';
            renderUserDropdown();
            onUserChanged();
            showToast(`欢迎新成员：${name}！`, 'success');
        } catch {}
    });

    // 回车添加
    document.getElementById('gate-new-name')?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            document.getElementById('gate-confirm-add').click();
        }
    });
}

// ========== 用户切换下拉菜单 ==========
function renderUserDropdown() {
    const containers = document.querySelectorAll('.user-switcher');
    containers.forEach(container => {
        const dropdown = container.querySelector('.user-dropdown');
        if (!dropdown) return;

        dropdown.innerHTML = members.map(m => `
            <button class="user-dropdown-item" data-id="${m.id}">
                <span class="dot" style="background:${m.color}"></span>
                ${m.name}
                ${currentUser && currentUser.id === m.id ? ' ✓' : ''}
            </button>
        `).join('') + `
            <hr style="border:none;border-top:1px solid var(--border);margin:4px 0">
            <button class="user-dropdown-item add-member-trigger">
                <span style="font-size:18px">＋</span> 添加成员
            </button>
        `;

        dropdown.querySelectorAll('.user-dropdown-item[data-id]').forEach(item => {
            item.addEventListener('click', () => {
                const id = parseInt(item.dataset.id);
                const member = members.find(m => m.id === id);
                if (member) {
                    setCurrentUser(member);
                    dropdown.classList.remove('show');
                    onUserChanged();
                }
            });
        });

        dropdown.querySelector('.add-member-trigger')?.addEventListener('click', () => {
            dropdown.classList.remove('show');
            showAddMemberModal();
        });
    });

    document.querySelectorAll('.current-user-badge').forEach(badge => {
        badge.onclick = (e) => {
            e.stopPropagation();
            const dropdown = badge.parentElement.querySelector('.user-dropdown');
            dropdown.classList.toggle('show');
        };
    });

    document.addEventListener('click', () => {
        document.querySelectorAll('.user-dropdown.show').forEach(d => d.classList.remove('show'));
    });
}

// ========== 添加成员弹窗 ==========
let memberModal = null;

function showAddMemberModal() {
    if (!memberModal) {
        memberModal = document.createElement('div');
        memberModal.className = 'modal-overlay';
        memberModal.innerHTML = `
            <div class="modal">
                <h3>添加家庭成员</h3>
                <div class="form-group">
                    <label>成员名称</label>
                    <input class="form-input" id="new-member-name" placeholder="例如：爷爷、奶奶..." style="width:100%">
                </div>
                <div class="modal-actions">
                    <button class="btn btn-outline cancel-btn">取消</button>
                    <button class="btn btn-primary confirm-btn">确认添加</button>
                </div>
            </div>
        `;
        document.body.appendChild(memberModal);

        memberModal.querySelector('.cancel-btn').onclick = () => memberModal.classList.remove('show');
        memberModal.querySelector('.confirm-btn').onclick = async () => {
            const input = document.getElementById('new-member-name');
            const name = input.value.trim();
            if (!name) {
                showToast('请输入名称', 'error');
                return;
            }
            try {
                const newMember = await api('/members', {
                    method: 'POST',
                    body: JSON.stringify({ name })
                });
                members.push(newMember);
                setCurrentUser(newMember);
                memberModal.classList.remove('show');
                input.value = '';
                renderUserDropdown();
                onUserChanged();
                showToast(`欢迎新成员：${name}！`, 'success');
            } catch {}
        };
    }
    memberModal.classList.add('show');
    setTimeout(() => {
        const input = document.getElementById('new-member-name');
        if (input) input.focus();
    }, 100);
}

// 用户切换后的回调（页面自行实现）
function onUserChanged() {
    // 由具体页面重写
}

// ========== 导航高亮 ==========
function highlightNav() {
    const path = window.location.pathname;
    document.querySelectorAll('.nav-links a').forEach(link => {
        link.classList.toggle('active', link.getAttribute('href') === path ||
            (path === '/' && link.getAttribute('href') === '/'));
    });
}

// ========== 认证检查 ==========
async function checkAuth() {
    try {
        const res = await fetch('/api/auth/status');
        const data = await res.json();
        if (!data.logged_in) {
            window.location.href = '/login';
            return false;
        }
        return true;
    } catch (err) {
        window.location.href = '/login';
        return false;
    }
}

async function doLogout() {
    try {
        await fetch('/api/auth/logout', { method: 'POST' });
    } catch {}
    localStorage.removeItem('family_current_user');
    window.location.href = '/login';
}

// ========== 初始化 ==========
async function initApp() {
    // 先检查登录状态
    const authed = await checkAuth();
    if (!authed) return;

    await loadMembers();

    // 先显示身份门
    await showIdentityGate();

    // 初始化 UI
    renderUserDropdown();
    updateUserUI();
    highlightNav();
}

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', initApp);
