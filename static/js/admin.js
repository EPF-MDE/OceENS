const AVATAR_COLORS = ['#7b2fa0', '#df231d', '#1565c0', '#2e7d32', '#e65100', '#ad1457', '#0277bd', '#558b2f'];
function parseMail(mail) {
    const parts = mail.split('@')[0].split('.');
    const cap = s => s.charAt(0).toUpperCase() + s.slice(1).toLowerCase();
    return { prenom: cap(parts[0]), nom: parts.length > 1 ? cap(parts[1]) : '' };
}

function getInitials(mail) {
    const { prenom, nom } = parseMail(mail);
    return ((prenom[0] || '') + (nom[0] || '')).toUpperCase();
}

function getRoleBadge(role) {
    const map = {
        'Etudiant': ['etudiant', 'Étudiant'],
        'Admin': ['admin', 'Administrateur'],
        'RPRM': ['rprm', 'RP-RM'],
        'Enseignant': ['enseignant', 'Enseignant'],
    };
    const [cls, label] = map[role] || ['etudiant', role];
    return `<span class="role-badge ${cls}"><span class="role-dot"></span>${label}</span>`;
}

// ── État global ──
let currentFilter = 'all';
let searchQuery = '';
let editingUserId = null;
let selectedRole = null;
let localUsers = ALL_USERS.map(u => ({ ...u }));

// ── Filtrage ──
function filteredUsers() {
    const q = searchQuery.toLowerCase();
    return localUsers.filter(u => {
        const { prenom, nom } = parseMail(u.mail);
        const matchSearch = !q || `${prenom} ${nom} ${u.mail}`.toLowerCase().includes(q);
        const matchFilter = currentFilter === 'all' || u.role === currentFilter;
        return matchSearch && matchFilter;
    });
}

// ── Rendu du tableau ──
function renderTable() {
    const tbody = document.getElementById('users-tbody');
    const empty = document.getElementById('empty-state');
    const table = document.getElementById('users-table');
    const count = document.getElementById('count-label');
    const list = filteredUsers();

    count.textContent = `${list.length} affiché(s)`;

    if (!list.length) {
        table.style.display = 'none';
        empty.style.display = 'block';
        return;
    }

    empty.style.display = 'none';
    table.style.display = '';

    tbody.innerHTML = list.map(u => {
        const { prenom, nom } = parseMail(u.mail);
        return `
        <tr data-id="${u.id_user}" data-role="${u.role}">
            <td>
                <div class="user-info">
                    <div class="avatar" style="background:${AVATAR_COLORS[u.id_user % 8]}">${getInitials(u.mail)}</div>
                    <div>
                        <div class="user-name">${prenom} ${nom}</div>
                        <div class="user-email">${u.mail}</div>
                    </div>
                </div>
            </td>
            <td>${getRoleBadge(u.role)}</td>
            <td class="td-actions"><button class="btn-edit" data-id="${u.id_user}">Modifier</button></td>
        </tr>`;
    }).join('');

    tbody.querySelectorAll('tr').forEach(tr => {
        tr.addEventListener('click', () => openModal(parseInt(tr.dataset.id)));
    });
}

// ── Modale ──
function openModal(userId) {
    const user = localUsers.find(u => u.id_user === userId);
    if (!user) return;
    editingUserId = userId;
    selectedRole = user.role;

    const { prenom, nom } = parseMail(user.mail);
    document.getElementById('modal-title').textContent = `${prenom} ${nom}`;
    document.getElementById('modal-subtitle').textContent = user.mail;

    document.querySelectorAll('.role-option').forEach(el => {
        el.classList.toggle('selected', el.dataset.role === selectedRole);
    });

    document.getElementById('btn-save').disabled = false;
    document.getElementById('modal-overlay').classList.add('open');
}

function closeModal() {
    document.getElementById('modal-overlay').classList.remove('open');
    editingUserId = null;
}

// ── Sélection du rôle dans la modale ──
document.querySelectorAll('.role-option').forEach(opt => {
    opt.addEventListener('click', () => {
        document.querySelectorAll('.role-option').forEach(o => o.classList.remove('selected'));
        opt.classList.add('selected');
        selectedRole = opt.dataset.role;
    });
});

// ── Sauvegarde ──
document.getElementById('btn-save').addEventListener('click', async () => {
    const user = localUsers.find(u => u.id_user === editingUserId);
    if (!user || !selectedRole) return;

    const btn = document.getElementById('btn-save');
    btn.disabled = true;
    btn.textContent = 'Enregistrement…';

    try {
        const resp = await fetch(`/api/users/${editingUserId}/role`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ role: selectedRole }),
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            throw new Error(err.detail || `HTTP ${resp.status}`);
        }
        user.role = selectedRole;
        closeModal();
        renderTable();
        const { prenom, nom } = parseMail(user.mail);
        showToast(`Rôle de ${prenom} ${nom} mis à jour`, 'success');
    } catch (err) {
        showToast(`Erreur : ${err.message}`, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Enregistrer';
    }
});

// ── Fermeture modale ──
document.getElementById('btn-cancel').addEventListener('click', closeModal);
document.getElementById('modal-overlay').addEventListener('click', e => {
    if (e.target === document.getElementById('modal-overlay')) closeModal();
});

// ── Recherche ──
document.getElementById('search-input').addEventListener('input', e => {
    searchQuery = e.target.value;
    renderTable();
});

// ── Filtres ──
document.querySelectorAll('.filter-tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        currentFilter = tab.dataset.filter;
        renderTable();
    });
});

// ── Toast ──
let toastTimer = null;
function showToast(msg, type = 'success') {
    const toast = document.getElementById('toast');
    document.getElementById('toast-msg').textContent = msg;
    toast.className = `toast ${type} show`;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove('show'), 3500);
}

// ── Init ──
document.querySelectorAll('#users-tbody tr').forEach(tr => {
    tr.addEventListener('click', () => openModal(parseInt(tr.dataset.id)));
});