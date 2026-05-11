// ═══════════════════════════════════════════════════════
//  Paramétrage — Module JS (données mockées, zéro backend)
//  Formulaire hiérarchique : Campus > Filière > UE > Module > Profs
// ═══════════════════════════════════════════════════════

const Parametrage = {
    container: null,

    campusList: [],
    allFilieres: [],
    profsList: [],
    templatesList: [],
    mockUEsByFiliere: {},

    // ─── État courant ───────────────────────────────────
    filieresList: [],
    selectedCampusId: null,
    selectedFiliereId: null,
    selectedTemplateId: null,
    semestreAnnee: '',
    anneesScolaires: [],
    selectedAnneeScolaire: '',
    ues: [],
    nextId: 9000,
    isLoading: false,
    loadError: null,

    // ─── Init ───────────────────────────────────────────
    init(containerId, initialData = {}) {
        this.container = document.getElementById(containerId);
        if (!this.container) return;

        this.templatesList = (initialData.templates || []).map(template => ({
            id: template.id_template,
            titre: template.nom
        }));
        this.campusList = initialData.campusList || [];
        this.allFilieres = initialData.filieres || [];
        this.profsList = initialData.profsList || [];
        this.mockUEsByFiliere = initialData.uesByFiliere || {};
        this.selectedCampusId = initialData.selectedCampusId || null;
        this.selectedFiliereId = initialData.selectedFiliereId || null;
        this.selectedTemplateId = initialData.selectedTemplateId || null;
        this.semestreAnnee = initialData.semestreAnnee || '';
        this.anneesScolaires = initialData.anneesScolaires || [];
        this.selectedAnneeScolaire = initialData.selectedAnneeScolaire || '';
        this.filieresList = this.selectedCampusId ? this.allFilieres.filter(f => f.campus_id === this.selectedCampusId) : [];
        if (this.selectedFiliereId && this.mockUEsByFiliere[this.selectedFiliereId]) {
            this.ues = JSON.parse(JSON.stringify(this.mockUEsByFiliere[this.selectedFiliereId]));
        }

        this.render();
    },

    // ─── Render principal ───────────────────────────────
    render() {
        this.container.innerHTML = `
            <div class="pub-header">
                <div class="pub-field">
                    <label>Modèle de questions</label>
                    <select id="param-template" onchange="Parametrage.selectedTemplateId = parseInt(this.value) || null;">
                        ${this.templatesList.map(t => `<option value="${t.id}" ${this.selectedTemplateId === t.id ? 'selected' : ''}>${t.titre}</option>`).join('')}
                    </select>
                </div>
                <div class="pub-field">
                    <label>Semestre</label>
                    <select id="param-semestre" onchange="Parametrage.semestreAnnee = this.value;">
                        <option value="">-- Sélectionnez un semestre --</option>
                        ${['S1','S2','S3','S4','S5','S6','S7','S8','S9','S10'].map(s => `<option value="${s}" ${this.semestreAnnee === s ? 'selected' : ''}>${s}</option>`).join('')}
                    </select>
                </div>
                <div class="pub-field">
                    <label>Année scolaire</label>
                    <div class="param-select-group" style="display: flex; gap: 10px; width: 100%;">
                        <select id="param-annee" onchange="Parametrage.selectedAnneeScolaire = this.value;" style="flex: 1;">
                            <option value="">-- Sélectionnez --</option>
                            ${this.anneesScolaires.map(a => `<option value="${a}" ${this.selectedAnneeScolaire === a ? 'selected' : ''}>${a}</option>`).join('')}
                        </select>
                        <button class="btn-icon" onclick="Parametrage.addAnneeScolaire()" title="Ajouter une année scolaire" style="flex-shrink: 0; padding: 0 15px; background: linear-gradient(135deg, #1a5276, #1f6f9f); color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold;">+</button>
                    </div>
                </div>
            </div>

            <hr style="border:0; border-top:1px solid #e0e6ec; margin:20px 0;">

            <div class="param-selectors">
                <div class="param-field">
                    <label>Campus</label>
                    <div class="param-select-group">
                        <select id="param-campus" onchange="Parametrage.onCampusChange()">
                            <option value="">-- Sélectionnez un campus --</option>
                            ${this.campusList.map(c => `<option value="${c.id}" ${this.selectedCampusId === c.id ? 'selected' : ''}>${c.nom}</option>`).join('')}
                        </select>
                    </div>
                </div>
                <div class="param-field">
                    <label>Filière</label>
                    <div class="param-select-group">
                        <select id="param-filiere" onchange="Parametrage.onFiliereChange()" ${!this.selectedCampusId ? 'disabled' : ''}>
                            <option value="">-- Sélectionnez une filière --</option>
                            ${this.filieresList.map(f => `<option value="${f.id}" ${this.selectedFiliereId === f.id ? 'selected' : ''}>${f.nom}</option>`).join('')}
                        </select>
                        <button class="btn-icon" onclick="Parametrage.addFiliere()" title="Créer une nouvelle filière" ${!this.selectedCampusId ? 'disabled style="opacity:0.5;cursor:not-allowed;"' : ''}>+</button>
                    </div>
                </div>
            </div>
            
            <div id="param-ue-container"></div>

            <button class="btn-publish" onclick="Parametrage.publish()" ${!this.selectedFiliereId ? 'disabled' : ''}>Publier le sondage</button>
        `;

        this.renderUEContainer();
    },

    // ─── Campus change ──────────────────────────────────
    async onCampusChange() {
        const sel = document.getElementById('param-campus');
        this.selectedCampusId = sel.value ? parseInt(sel.value) : null;
        this.selectedFiliereId = null;

        if (this.selectedCampusId) {
            this.filieresList = this.allFilieres.filter(f => f.campus_id === this.selectedCampusId);
        } else {
            this.filieresList = [];
        }
        this.render();
        await this.fetchAndUpdateData();
    },

    renderUEContainer() {
        const container = document.getElementById('param-ue-container');
        if (!container) return;

        if (this.loadError) {
            container.innerHTML = `<p class="param-empty">${this.esc(this.loadError)}</p>`;
            return;
        }

        if (this.isLoading && !this.selectedFiliereId) {
            container.innerHTML = `<p class="param-empty">Chargement des filières...</p>`;
            return;
        }

        if (!this.selectedCampusId && !this.selectedFiliereId) {
            container.innerHTML = `<p class="param-empty">Sélectionnez un campus et une filière pour configurer les cours et professeurs.</p>`;
            return;
        }

        if (this.selectedCampusId && !this.selectedFiliereId) {
            if (this.filieresList.length === 0) {
                container.innerHTML = `<p class="param-empty">Aucune filière disponible pour ce campus.</p>`;
                return;
            }
            container.innerHTML = `<p class="param-empty">Sélectionnez une filière pour configurer les cours et professeurs.</p>`;
            return;
        }

        if (this.selectedFiliereId) {
            this.renderUEs();
            return;
        }

        container.innerHTML = '';
    },

    async fetchAndUpdateData() {
        if (!window.fetch) return;

        this.isLoading = true;
        this.loadError = null;
        this.renderUEContainer();

        try {
            const response = await fetch('/api/parametrage', { cache: 'no-store' });
            if (!response.ok) {
                throw new Error(`Impossible de charger les données : ${response.status}`);
            }
            const data = await response.json();

            this.campusList = data.campusList || this.campusList;
            this.allFilieres = data.filieres || this.allFilieres;
            this.profsList = data.profsList || this.profsList;
            this.templatesList = (data.templates || []).map(template => ({
                id: template.id_template,
                titre: template.nom
            }));
            this.mockUEsByFiliere = data.uesByFiliere || this.mockUEsByFiliere;
            if (data.anneesScolaires) this.anneesScolaires = data.anneesScolaires;
            if (data.selectedAnneeScolaire && !this.selectedAnneeScolaire) this.selectedAnneeScolaire = data.selectedAnneeScolaire;

            if (this.selectedCampusId) {
                this.filieresList = this.allFilieres.filter(f => f.campus_id === this.selectedCampusId);
            } else {
                this.filieresList = [];
            }

            if (this.selectedFiliereId) {
                this.ues = JSON.parse(JSON.stringify(this.mockUEsByFiliere[this.selectedFiliereId] || []));
            }
        } catch (error) {
            this.loadError = error.message || 'Une erreur est survenue pendant le chargement.';
        } finally {
            this.isLoading = false;
            this.render();
        }
    },



    // ─── Filière change ─────────────────────────────────
    async onFiliereChange() {
        const sel = document.getElementById('param-filiere');
        this.selectedFiliereId = sel.value ? parseInt(sel.value) : null;
        if (this.selectedFiliereId) {
            this.ues = JSON.parse(JSON.stringify(this.mockUEsByFiliere[this.selectedFiliereId] || []));
        } else {
            this.ues = [];
        }
        this.render();
        await this.fetchAndUpdateData();
    },

    addFiliere() {
        if (!this.selectedCampusId) return alert("Veuillez d'abord sélectionner ou créer un campus.");
        const nom = prompt('Nom de la nouvelle filière :');
        if (!nom || !nom.trim()) return;
        const newId = ++this.nextId;
        const newFiliere = { id: newId, nom: nom.trim(), campus_id: this.selectedCampusId };
        this.allFilieres.push(newFiliere);
        this.filieresList.push(newFiliere);
        this.selectedFiliereId = newId;
        this.ues = [];
        this.render();
    },

    addAnneeScolaire() {
        const nouvelleAnnee = prompt("Saisissez la nouvelle année scolaire (ex: 2024-2025) :");
        if (!nouvelleAnnee || !nouvelleAnnee.trim()) return;
        const annee = nouvelleAnnee.trim();
        if (!this.anneesScolaires.includes(annee)) {
            this.anneesScolaires.push(annee);
        }
        this.selectedAnneeScolaire = annee;
        this.render();
    },

    // ─── Render la liste des UE ─────────────────────────
    renderUEs() {
        const container = document.getElementById('param-ue-container');
        if (!container) return;

        if (this.isLoading) {
            container.innerHTML = `
                <p class="param-empty">Chargement des données pour la filière...</p>
            `;
            return;
        }

        if (this.ues.length === 0) {
            container.innerHTML = `
                <p class="param-empty">Aucune UE pour cette filière.</p>
                <button class="param-btn-add param-btn-add-ue" onclick="Parametrage.addUE()">+ Ajouter une UE</button>
            `;
            return;
        }

        container.innerHTML = `
            <div class="param-ue-list">
                ${this.ues.map((ue, i) => this.renderUE(ue, i)).join('')}
            </div>
            <button class="param-btn-add param-btn-add-ue" onclick="Parametrage.addUE()">+ Ajouter une UE</button>
        `;
    },

    // ─── Render une UE ──────────────────────────────────
    renderUE(ue, index) {
        const isOpen = ue._open !== false;
        return `
            <div class="param-ue ${isOpen ? 'open' : ''}" data-ue-id="${ue.id}">
                <div class="param-ue-header" onclick="Parametrage.toggleUE(${ue.id})">
                    <span class="param-chevron"></span>
                    <span class="param-ue-name">
                        <input type="text" value="${this.esc(ue.nom)}"
                               onclick="event.stopPropagation()"
                               onblur="Parametrage.renameUE(${ue.id}, this.value)"
                               onkeydown="if(event.key==='Enter'){this.blur();}">
                    </span>
                    ${ue.optionnel ? '<span class="param-badge-optionnel">Optionnelle</span>' : ''}
                    <span class="param-ue-actions" onclick="event.stopPropagation()">
                        <label><input type="checkbox" ${ue.optionnel ? 'checked' : ''} onchange="Parametrage.toggleOptional(${ue.id}, this.checked)"> Opt.</label>
                        <button class="param-btn-remove" onclick="Parametrage.removeUE(${ue.id})" title="Supprimer l'UE">&times;</button>
                    </span>
                </div>
                <div class="param-ue-body">
                    <div class="param-module-list">
                        ${(ue.modules || []).map(m => this.renderModule(m, ue.id)).join('')}
                    </div>
                    <button class="param-btn-add" onclick="Parametrage.addModule(${ue.id})">+ Ajouter un module</button>
                </div>
            </div>
        `;
    },

    // ─── Render un Module ───────────────────────────────
    renderModule(mod, ueId) {
        const assignedIds = (mod.professeurs || []).map(p => p.id);
        const availableProfs = this.profsList.filter(p => !assignedIds.includes(p.id));

        return `
            <div class="param-module" data-module-id="${mod.id}">
                <div class="param-module-name">
                    <input type="text" value="${this.esc(mod.nom)}" placeholder="Nom du module"
                           onblur="Parametrage.renameModule(${mod.id}, this.value, ${ueId})"
                           onkeydown="if(event.key==='Enter'){this.blur();}">
                </div>
                <div class="param-module-modalite">
                    <label class="param-checkbox-label">
                        <input type="checkbox" ${mod.choix_enseignant_exclusif ? 'checked' : ''}
                               onchange="Parametrage.toggleChoixEnseignant(${mod.id}, this.checked, ${ueId})">
                        <span>1 seul enseignant parmi la liste</span>
                    </label>
                </div>
                <div class="param-module-profs">
                    <ul class="param-prof-list">
                        ${(mod.professeurs || []).map(p => `
                            <li class="param-prof-item">
                                <span class="param-prof-name">${this.esc(p.prenom)} ${this.esc(p.nom)}</span>
                                <button class="param-remove-tag" onclick="Parametrage.removeProf(${mod.id}, ${p.id}, ${ueId})">&times;</button>
                            </li>
                        `).join('')}
                    </ul>
                    <span class="param-prof-dropdown">
                        <button class="param-add-prof-btn" onclick="Parametrage.toggleProfDropdown(${mod.id})">+ Prof</button>
                        <div class="param-prof-dropdown-content" id="prof-dd-${mod.id}">
                            <div class="param-prof-option param-prof-option-new" onclick="Parametrage.createNewProf(${mod.id}, ${ueId})">
                                + Créer un nouveau professeur
                            </div>
                            ${availableProfs.length === 0 ? '<div class="param-prof-option" style="color:#999;">Aucun prof disponible</div>' :
                availableProfs.map(p => `
                                <div class="param-prof-option" onclick="Parametrage.addProf(${mod.id}, ${p.id}, ${ueId})">
                                    ${this.esc(p.prenom)} ${this.esc(p.nom)}
                                </div>
                              `).join('')}
                        </div>
                    </span>
                </div>
                <button class="param-btn-remove" onclick="Parametrage.removeModule(${mod.id}, ${ueId})" title="Supprimer le module">&times;</button>
            </div>
        `;
    },

    // ─── Actions UE ─────────────────────────────────────
    toggleUE(ueId) {
        const ue = this.ues.find(u => u.id === ueId);
        if (ue) {
            ue._open = ue._open === false ? true : false;
            this.renderUEs();
        }
    },

    addUE() {
        if (!this.selectedFiliereId) return;
        const nom = prompt('Nom de la nouvelle UE :');
        if (!nom || !nom.trim()) return;
        const newId = ++this.nextId;
        this.ues.push({
            id: newId,
            nom: nom.trim(),
            filiere_id: this.selectedFiliereId,
            optionnel: false,
            _open: true,
            modules: []
        });
        this.renderUEs();
    },

    renameUE(ueId, newName) {
        if (!newName || !newName.trim()) return;
        const ue = this.ues.find(u => u.id === ueId);
        if (ue) ue.nom = newName.trim();
    },

    toggleOptional(ueId, checked) {
        const ue = this.ues.find(u => u.id === ueId);
        if (ue) {
            ue.optionnel = checked;
            this.renderUEs();
        }
    },

    removeUE(ueId) {
        if (!confirm('Supprimer cette UE et tous ses modules ?')) return;
        this.ues = this.ues.filter(u => u.id !== ueId);
        this.renderUEs();
    },

    // ─── Actions Module ─────────────────────────────────
    addModule(ueId) {
        const ue = this.ues.find(u => u.id === ueId);
        if (!ue) return;
        const newId = ++this.nextId;
        if (!ue.modules) ue.modules = [];
        ue.modules.push({
            id: newId,
            nom: 'Nouveau module',
            ue_id: ueId,
            choix_enseignant_exclusif: false,
            professeurs: []
        });
        ue._open = true;
        this.renderUEs();
    },

    renameModule(modId, newName, ueId) {
        if (!newName || !newName.trim()) return;
        const ue = this.ues.find(u => u.id === ueId);
        if (!ue) return;
        const mod = (ue.modules || []).find(m => m.id === modId);
        if (mod) mod.nom = newName.trim();
    },

    toggleChoixEnseignant(modId, checked, ueId) {
        const ue = this.ues.find(u => u.id === ueId);
        if (!ue) return;
        const mod = (ue.modules || []).find(m => m.id === modId);
        if (mod) mod.choix_enseignant_exclusif = checked;
    },

    removeModule(modId, ueId) {
        if (!confirm('Supprimer ce module ?')) return;
        const ue = this.ues.find(u => u.id === ueId);
        if (!ue) return;
        ue.modules = (ue.modules || []).filter(m => m.id !== modId);
        ue._open = true;
        this.renderUEs();
    },

    // ─── Actions Professeur ─────────────────────────────
    toggleProfDropdown(modId) {
        document.querySelectorAll('.param-prof-dropdown-content.show').forEach(el => {
            if (el.id !== 'prof-dd-' + modId) el.classList.remove('show');
        });
        const dd = document.getElementById('prof-dd-' + modId);
        if (dd) dd.classList.toggle('show');
    },

    addProf(modId, profId, ueId) {
        const dd = document.getElementById('prof-dd-' + modId);
        if (dd) dd.classList.remove('show');

        const ue = this.ues.find(u => u.id === ueId);
        if (!ue) return;
        const mod = (ue.modules || []).find(m => m.id === modId);
        if (!mod) return;

        const prof = this.profsList.find(p => p.id === profId);
        if (!prof) return;
        if (!mod.professeurs) mod.professeurs = [];
        mod.professeurs.push({ ...prof });
        ue._open = true;
        this.renderUEs();
    },

    createNewProf(modId, ueId) {
        const dd = document.getElementById('prof-dd-' + modId);
        if (dd) dd.classList.remove('show');

        const prenom = prompt('Prénom du professeur :');
        if (!prenom || !prenom.trim()) return;
        const nom = prompt('Nom du professeur :');
        if (!nom || !nom.trim()) return;

        const newId = ++this.nextId;
        const newProf = { id: newId, nom: nom.trim(), prenom: prenom.trim() };
        this.profsList.push(newProf);
        this.addProf(modId, newId, ueId);
    },

    removeProf(modId, profId, ueId) {
        const ue = this.ues.find(u => u.id === ueId);
        if (!ue) return;
        const mod = (ue.modules || []).find(m => m.id === modId);
        if (!mod) return;
        mod.professeurs = (mod.professeurs || []).filter(p => p.id !== profId);
        ue._open = true;
        this.renderUEs();
    },

    // ─── Publication (simulée) ──────────────────────────
    publish() {
        if (!this.selectedTemplateId) {
            this.selectedTemplateId = this.templatesList[0]?.id;
        }
        if (!this.selectedCampusId) return alert('Veuillez sélectionner un Campus.');
        if (!this.selectedFiliereId) return alert('Veuillez sélectionner une Filière.');
        if (!this.semestreAnnee || !this.semestreAnnee.trim()) return alert("Veuillez sélectionner un semestre.");
        if (!this.selectedAnneeScolaire || !this.selectedAnneeScolaire.trim()) return alert("Veuillez sélectionner une année scolaire.");
        if (this.ues.length === 0) return alert('Le sondage doit contenir au moins une UE.');

        const campusNom = this.campusList.find(c => c.id === this.selectedCampusId)?.nom || '';
        const filiereNom = this.filieresList.find(f => f.id === this.selectedFiliereId)?.nom || '';

        // Préparer les données avec les UEs, modules et professeurs
        const data = {
            id_template: this.selectedTemplateId,
            campus: campusNom,
            formation: filiereNom,
            semestre: this.semestreAnnee,
            annee_scolaire: this.selectedAnneeScolaire,
            ues: this.ues.map(ue => ({
                id: ue.id,
                nom: ue.nom,
                optionnel: ue.optionnel,
                modules: (ue.modules || []).map(mod => ({
                    id: mod.id,
                    nom: mod.nom,
                    choix_enseignant_exclusif: mod.choix_enseignant_exclusif || false,
                    professeurs: (mod.professeurs || []).map(prof => ({
                        id: prof.id,
                        prenom: prof.prenom,
                        nom: prof.nom
                    }))
                }))
            }))
        };

        fetch('/api/sondage', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Erreur réseau');
            }
            return response.json();
        })
        .then(result => {
            alert(result.message + '\nLien du questionnaire : ' + window.location.origin + result.questionnaire_url);
            // Rediriger vers le questionnaire généré
            window.location.href = result.questionnaire_url;
        })
        .catch(error => {
            alert('Erreur lors de la création du sondage : ' + error.message);
            console.error(error);
        });
    },

    // ─── Utils ──────────────────────────────────────────
    esc(str) {
        const div = document.createElement('div');
        div.textContent = str || '';
        return div.innerHTML;
    }
};

// Fermer les dropdowns profs au clic extérieur
document.addEventListener('click', function (e) {
    if (!e.target.closest('.param-prof-dropdown')) {
        document.querySelectorAll('.param-prof-dropdown-content.show').forEach(el => el.classList.remove('show'));
    }
});
