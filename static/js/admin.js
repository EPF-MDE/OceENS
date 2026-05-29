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
    if (!role) return '';
    if (role === 'Etudiant') return `<span class="role-badge etudiant"><span class="role-dot"></span>Étudiant</span>`;
    if (role === 'Admin') return `<span class="role-badge admin"><span class="role-dot"></span>Administrateur</span>`;
    if (role === 'Enseignant') return `<span class="role-badge enseignant"><span class="role-dot"></span>Enseignant</span>`;
    if (role.startsWith('RP-RM')) {
        const parts = role.split(':');
        const label = parts.length > 1 ? `RP-RM : ${parts[1]}` : 'RP-RM';
        return `<span class="role-badge rprm"><span class="role-dot"></span>${label}</span>`;
    }
    return `<span class="role-badge rprm"><span class="role-dot"></span>${role}</span>`;
}

// ── État global ──
let currentFilter = 'all';
let searchQuery = '';
let editingUserId = null;
let selectedRole = null;
let selectedFormations = [];   // ← NOUVEAU : formations RP-RM sélectionnées
let localUsers = ALL_USERS.map(u => ({ ...u }));

// ── NOUVEAU : Extraire toutes les formations existantes depuis les rôles RP-RM ──
function getExistingFormations() {
    const formations = new Set();
    localUsers.forEach(u => {
        if (u.role && u.role.startsWith('RP-RM:')) {
            const after = u.role.split(':')[1];
            if (after) {
                after.split(',').forEach(f => {
                    const t = f.trim();
                    if (t) formations.add(t);
                });
            }
        }
    });
    return Array.from(formations).sort();
}

// ── Filtrage ──
function filteredUsers() {
    const q = searchQuery.toLowerCase();
    return localUsers.filter(u => {
        const { prenom, nom } = parseMail(u.mail);
        const matchSearch = !q || `${prenom} ${nom} ${u.mail}`.toLowerCase().includes(q);
        let matchFilter = currentFilter === 'all';
        if (!matchFilter) {
            if (currentFilter === 'RP-RM') {
                matchFilter = u.role && u.role.startsWith('RP-RM');
            } else {
                matchFilter = u.role === currentFilter;
            }
        }
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

// ── NOUVEAU : Rendu des tags formations ──
function renderFormationTags() {
    const container = document.getElementById('formations-tags');
    container.innerHTML = selectedFormations.map(f => `
        <span class="formation-tag">
            ${f}
            <button class="formation-tag-remove" data-formation="${f}" title="Retirer">×</button>
        </span>
    `).join('');

    container.querySelectorAll('.formation-tag-remove').forEach(btn => {
        btn.addEventListener('click', () => {
            selectedFormations = selectedFormations.filter(f => f !== btn.dataset.formation);
            renderFormationTags();
        });
    });
}

// ── NOUVEAU : Rafraîchir le dropdown des formations ──
function refreshFormationsDropdown() {
    const select = document.getElementById('formations-select');
    const existing = getExistingFormations();
    select.innerHTML = `<option value="">-- Sélectionner une formation --</option>`;
    existing.forEach(f => {
        if (!selectedFormations.includes(f)) {
            const opt = document.createElement('option');
            opt.value = f;
            opt.textContent = f;
            select.appendChild(opt);
        }
    });
    const newOpt = document.createElement('option');
    newOpt.value = '__new__';
    newOpt.textContent = '+ Créer une nouvelle formation';
    select.appendChild(newOpt);
}

// ── NOUVEAU : Afficher/masquer la section formations ──
function toggleRprmSection(show) {
    document.getElementById('rprm-formations-section').classList.toggle('visible', show);
}

// ── Modale ──
function openModal(userId) {
    const user = localUsers.find(u => u.id_user === userId);
    if (!user) return;
    editingUserId = userId;

    // MODIFIÉ : détecter si RP-RM et extraire les formations
    if (user.role && user.role.startsWith('RP-RM')) {
        selectedRole = 'RP-RM';
        const parts = user.role.split(':');
        selectedFormations = parts.length > 1
            ? parts[1].split(',').map(f => f.trim()).filter(Boolean)
            : [];
    } else {
        selectedRole = user.role || 'Etudiant';
        selectedFormations = [];
    }

    const { prenom, nom } = parseMail(user.mail);
    document.getElementById('modal-title').textContent = `${prenom} ${nom}`;
    document.getElementById('modal-subtitle').textContent = user.mail;

    document.querySelectorAll('.role-option').forEach(el => {
        el.classList.toggle('selected', el.dataset.role === selectedRole);
    });

    // NOUVEAU : initialiser la section formations
    toggleRprmSection(selectedRole === 'RP-RM');
    renderFormationTags();
    refreshFormationsDropdown();
    document.getElementById('new-formation-row').classList.remove('visible');

    document.getElementById('btn-save').disabled = false;
    document.getElementById('modal-overlay').classList.add('open');
}

function closeModal() {
    document.getElementById('modal-overlay').classList.remove('open');
    document.getElementById('new-formation-row').classList.remove('visible');
    document.getElementById('new-formation-input').value = '';
    editingUserId = null;
}

// ── Sélection du rôle dans la modale ──
document.querySelectorAll('.role-option').forEach(opt => {
    opt.addEventListener('click', () => {
        document.querySelectorAll('.role-option').forEach(o => o.classList.remove('selected'));
        opt.classList.add('selected');
        selectedRole = opt.dataset.role;

        // NOUVEAU : afficher/masquer section formations
        if (selectedRole === 'RP-RM') {
            toggleRprmSection(true);
            refreshFormationsDropdown();
        } else {
            toggleRprmSection(false);
            selectedFormations = [];
        }
    });
});

// ── NOUVEAU : Ajouter une formation depuis le dropdown ──
document.getElementById('btn-add-formation').addEventListener('click', () => {
    const select = document.getElementById('formations-select');
    const val = select.value;
    if (!val) return;

    if (val === '__new__') {
        document.getElementById('new-formation-row').classList.add('visible');
        document.getElementById('new-formation-input').focus();
        select.value = '';
        return;
    }

    if (!selectedFormations.includes(val)) {
        selectedFormations.push(val);
        renderFormationTags();
        refreshFormationsDropdown();
    }
    select.value = '';
});

// ── NOUVEAU : Confirmer la nouvelle formation ──
document.getElementById('btn-confirm-formation').addEventListener('click', () => {
    const input = document.getElementById('new-formation-input');
    const val = input.value.trim();
    if (!val) return;

    if (!selectedFormations.includes(val)) {
        selectedFormations.push(val);
        renderFormationTags();
        refreshFormationsDropdown();
    }
    input.value = '';
    document.getElementById('new-formation-row').classList.remove('visible');
});

// ── NOUVEAU : Annuler nouvelle formation ──
document.getElementById('btn-cancel-new-formation').addEventListener('click', () => {
    document.getElementById('new-formation-input').value = '';
    document.getElementById('new-formation-row').classList.remove('visible');
});

// ── NOUVEAU : Entrée clavier sur le champ nouvelle formation ──
document.getElementById('new-formation-input').addEventListener('keydown', e => {
    if (e.key === 'Enter') { e.preventDefault(); document.getElementById('btn-confirm-formation').click(); }
    if (e.key === 'Escape') { document.getElementById('btn-cancel-new-formation').click(); }
});

// ── Sauvegarde ──
document.getElementById('btn-save').addEventListener('click', async () => {
    const user = localUsers.find(u => u.id_user === editingUserId);
    if (!user || !selectedRole) return;

    // MODIFIÉ : construire le rôle final avec les formations
    let finalRole = selectedRole;
    if (selectedRole === 'RP-RM') {
        finalRole = selectedFormations.length > 0
            ? `RP-RM:${selectedFormations.join(',')}`
            : 'RP-RM';
    }

    const btn = document.getElementById('btn-save');
    btn.disabled = true;
    btn.textContent = 'Enregistrement…';

    try {
        const resp = await fetch(`/api/users/${editingUserId}/role`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ role: finalRole }),
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            throw new Error(err.detail || `HTTP ${resp.status}`);
        }
        user.role = finalRole;
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